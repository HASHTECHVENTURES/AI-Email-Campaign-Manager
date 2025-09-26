#!/usr/bin/env python3
"""
AI Email Campaign Manager - Clean Local Version
Optimized for local development and production use
"""

from flask import Flask, render_template, request, jsonify
import smtplib
import imaplib
import email
from email.message import EmailMessage
from datetime import datetime
import requests
import json
import pandas as pd
import io
import re
import dns.resolver
import socket
import threading
import time
import os

app = Flask(__name__)

# Email Configuration (Production Ready)
EMAIL = os.getenv('EMAIL', 'karmaterra427@gmail.com')
PASSWORD = os.getenv('PASSWORD', 'jidw kfwg hpsh diqi')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# IMAP Configuration for reading emails
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

# Gemini AI Configuration (Production Ready)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Data Storage
contacts = []
sent_emails = []
replies = []
conversations = []  # Store AI conversations
unanswered_emails = []  # Track emails with no replies

# Email monitoring
email_monitoring_active = False
last_email_check = None
monitoring_thread = None

# Email sending limits
DAILY_EMAIL_LIMIT = 100  # Maximum emails per day
HOURLY_EMAIL_LIMIT = 20  # Maximum emails per hour
EMAIL_SENDING_COOLDOWN = 1  # Seconds between emails

# Analytics
email_analytics = {
    'total_sent': 0,
    'total_replies': 0,
    'response_rate': 0.0,
    'ai_auto_replies': 0,
    'manual_replies': 0
}

def calculate_analytics():
    """Calculate email analytics"""
    global email_analytics, sent_emails, replies
    
    email_analytics['total_sent'] = len(sent_emails)
    email_analytics['total_replies'] = len(replies)
    
    if email_analytics['total_sent'] > 0:
        email_analytics['response_rate'] = round((email_analytics['total_replies'] / email_analytics['total_sent']) * 100, 2)
    else:
        email_analytics['response_rate'] = 0.0
    
    return email_analytics

def validate_email_format(email):
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_domain_exists(domain):
    """Check if email domain exists using DNS"""
    # Known fake/test domains for demonstration (excluding example.com for testing)
    fake_domains = ['fake.com', 'invalid.email', 'notreal.domain', 'bounce.test', 'fake.test', 'example.fake']
    if domain.lower() in fake_domains:
        return False
        
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except:
        try:
            dns.resolver.resolve(domain, 'A')
            return True
        except:
            return False

def validate_email_deliverability(email):
    """Simple email format validation only"""
    print(f"📧 Validating email: {email}")
    
    # Only check basic format
    if not validate_email_format(email):
        return {'valid': False, 'reason': 'Invalid email format', 'confidence': 100, 'category': 'format_error'}
    
    # Accept all properly formatted emails
    print(f"✅ Email accepted: {email}")
    return {
        'valid': True, 
        'reason': 'Email format is valid', 
        'confidence': 100,
        'category': 'valid_email'
    }

def get_email_limits_status():
    """Get current email sending limits status"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    today = now.date()
    current_hour = now.hour
    
    # Count emails sent today
    today_emails = [email for email in sent_emails 
                   if datetime.fromisoformat(email['timestamp']).date() == today]
    
    # Count emails sent in current hour
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_emails = [email for email in sent_emails 
                  if datetime.fromisoformat(email['timestamp']) >= hour_start]
    
    return {
        'daily_limit': DAILY_EMAIL_LIMIT,
        'hourly_limit': HOURLY_EMAIL_LIMIT,
        'daily_sent': len(today_emails),
        'hourly_sent': len(hour_emails),
        'daily_remaining': max(0, DAILY_EMAIL_LIMIT - len(today_emails)),
        'hourly_remaining': max(0, HOURLY_EMAIL_LIMIT - len(hour_emails)),
        'can_send_daily': len(today_emails) < DAILY_EMAIL_LIMIT,
        'can_send_hourly': len(hour_emails) < HOURLY_EMAIL_LIMIT,
        'cooldown_seconds': EMAIL_SENDING_COOLDOWN
    }

def can_send_email():
    """Check if email sending is allowed based on limits"""
    status = get_email_limits_status()
    return status['can_send_daily'] and status['can_send_hourly']

def track_email_sent(recipient, subject, campaign_type="Manual"):
    """Track sent emails with reply tracking"""
    global sent_emails, email_analytics, unanswered_emails
    
    email_record = {
        'id': len(sent_emails) + 1,
        'recipient': recipient,
        'subject': subject,
        'campaign_type': campaign_type,
        'sent_date': datetime.now().isoformat(),
        'status': 'sent',
        'replied': False,
        'reply_count': 0,
        'last_activity': datetime.now().isoformat()
    }
    
    sent_emails.append(email_record)
    # Add to unanswered emails initially
    unanswered_emails.append({
        'email_id': email_record['id'],
        'recipient': recipient,
        'subject': subject,
        'sent_date': email_record['sent_date'],
        'days_since_sent': 0
    })
    
    email_analytics['total_sent'] += 1

# Email Monitoring Functions
def check_for_new_emails():
    """Check for new email replies using IMAP"""
    global last_email_check, replies, conversations, sent_emails, unanswered_emails
    
    try:
        print("📧 Checking for new email replies...")
        
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select('INBOX')
        
        # Search for emails since last check (or last 24 hours if first time)
        if last_email_check:
            # Search for emails since last check
            search_criteria = f'(SINCE "{last_email_check.strftime("%d-%b-%Y")}")'
        else:
            # First time - check last 24 hours
            from datetime import timedelta
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{yesterday}")'
        
        status, messages = mail.search(None, search_criteria)
        
        if status == 'OK':
            email_ids = messages[0].split()
            new_replies_count = 0
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                        
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email details
                    sender_email = email_message.get('From', '')
                    subject = email_message.get('Subject', '')
                    date_received = email_message.get('Date', '')
                    
                    # Clean sender email (remove name if present)
                    if '<' in sender_email and '>' in sender_email:
                        sender_email = sender_email.split('<')[1].split('>')[0]
                    
                    # Skip emails from our own address
                    if sender_email.lower() == EMAIL.lower():
                        continue
                    
                    # Check if this is a reply to one of our sent emails
                    is_reply = False
                    original_email = None
                    
                    # Look for "Re:" in subject or check if we sent to this email
                    if 'Re:' in subject or 'RE:' in subject:
                        # Find original sent email
                        for sent_email in sent_emails:
                            if sent_email['recipient'].lower() == sender_email.lower():
                                original_email = sent_email
                                is_reply = True
                break
        
                    if is_reply and original_email:
                        # Extract message content
                        message_content = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    message_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            message_content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        # Clean message content (remove quoted text)
                        lines = message_content.split('\n')
                        clean_lines = []
                        for line in lines:
                            if line.strip().startswith('>') or 'wrote:' in line or 'On ' in line and 'at ' in line:
                                break
                            clean_lines.append(line)
                        message_content = '\n'.join(clean_lines).strip()
                        
                        # Extract sender name
                        sender_name = sender_email.split('@')[0].replace('.', ' ').title()
                        
                        # Check if we already processed this reply
                        already_processed = any(
                            r.get('from_email', '').lower() == sender_email.lower() and 
                            r.get('subject', '') == subject and
                            r.get('content', '') == message_content
                            for r in replies
                        )
                        
                        if not already_processed and message_content:
                            print(f"📨 New reply from {sender_email}: {subject}")
                            
                            # Add to replies
                            reply_record = {
                                'id': len(replies) + 1,
                                'from_email': sender_email,
                                'from_name': sender_name,
                                'subject': subject,
                                'content': message_content,
                                'received_date': datetime.now().isoformat(),
                                'original_email_id': original_email['id']
                            }
                            replies.append(reply_record)
                            
                            # Process the reply and generate AI response
                            conversation = process_incoming_reply(sender_email, sender_name, subject, message_content)
                            
                            new_replies_count += 1
                            print(f"✅ Processed reply from {sender_name} and sent AI response")
                
                except Exception as e:
                    print(f"❌ Error processing email {email_id}: {str(e)}")
                    continue
            
            print(f"📊 Email check complete. Found {new_replies_count} new replies.")
            last_email_check = datetime.now()
            
        mail.close()
        mail.logout()
        
        return new_replies_count
        
    except Exception as e:
        print(f"❌ Error checking emails: {str(e)}")
        return 0

def start_email_monitoring():
    """Start background email monitoring"""
    global email_monitoring_active, monitoring_thread
    
    if email_monitoring_active:
        return
    
    email_monitoring_active = True
    
    def monitoring_loop():
        while email_monitoring_active:
            try:
                check_for_new_emails()
                # Check every 30 seconds
                time.sleep(30)
    except Exception as e:
                print(f"❌ Monitoring error: {str(e)}")
                time.sleep(60)  # Wait longer on error
    
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    print("🔄 Email monitoring started - checking every 30 seconds")

def stop_email_monitoring():
    """Stop background email monitoring"""
    global email_monitoring_active
    email_monitoring_active = False
    print("⏹️ Email monitoring stopped")

def generate_ai_reply(original_message, sender_name="", conversation_history=None):
    """Generate AI reply using Gemini API with conversation context"""
    try:
        # Build conversation context
        context = ""
        if conversation_history:
            context = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                role = "Customer" if msg['sender_type'] == 'customer' else "AI Assistant"
                context += f"{role}: {msg['content']}\n"
        
        prompt = f"""
        You are a professional AI email assistant representing a business. You are engaging in an ongoing conversation with a potential customer.
        
        Customer Name: {sender_name}
        Latest message from customer:
        {original_message}
        {context}
        
        Generate a response that is:
        - Professional, friendly, and engaging
        - Helpful and informative about our services
        - Maintains conversation flow and context
        - Asks relevant follow-up questions
        - Aims to move the conversation toward a business opportunity
        - Concise (2-3 paragraphs max)
        - Ends with a clear question or call to action
        
        Do not include subject line or email headers, just the message body.
        Sign off as "Best regards, AI Assistant"
        """
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            ai_reply = result['candidates'][0]['content']['parts'][0]['text']
            return ai_reply.strip()
        else:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"AI Reply Error: {str(e)}")
        return None

def process_incoming_reply(sender_email, sender_name, subject, message_content):
    """Process incoming email reply and generate AI response"""
    global conversations, replies, sent_emails, unanswered_emails
    
    # Find the original sent email
    original_email = None
    for email in sent_emails:
        if email['recipient'].lower() == sender_email.lower():
            original_email = email
            break
    
    if original_email:
        # Mark as replied
        original_email['replied'] = True
        original_email['reply_count'] += 1
        original_email['last_activity'] = datetime.now().isoformat()
        
        # Remove from unanswered emails
        unanswered_emails = [ue for ue in unanswered_emails if ue['email_id'] != original_email['id']]
    
    # Find or create conversation
    conversation = None
    for conv in conversations:
        if conv['customer_email'].lower() == sender_email.lower():
            conversation = conv
            break
    
    if not conversation:
        conversation = {
            'id': len(conversations) + 1,
            'customer_email': sender_email,
            'customer_name': sender_name,
            'started_date': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'status': 'active',
            'message_count': 0,
            'messages': []
        }
        conversations.append(conversation)
    
    # Add customer message to conversation
    customer_message = {
        'id': len(conversation['messages']) + 1,
        'sender_type': 'customer',
        'sender_name': sender_name,
        'content': message_content,
        'timestamp': datetime.now().isoformat(),
        'subject': subject
    }
    conversation['messages'].append(customer_message)
    conversation['message_count'] += 1
    conversation['last_activity'] = datetime.now().isoformat()
    
    # Generate AI response
    ai_response = generate_ai_reply(message_content, sender_name, conversation['messages'])
    
    if ai_response:
        # Add AI message to conversation
        ai_message = {
            'id': len(conversation['messages']) + 1,
            'sender_type': 'ai',
            'sender_name': 'AI Assistant',
            'content': ai_response,
            'timestamp': datetime.now().isoformat(),
            'subject': f"Re: {subject.replace('Re: ', '')}"
        }
        conversation['messages'].append(ai_message)
        conversation['message_count'] += 1
        conversation['last_activity'] = datetime.now().isoformat()
        
        # Send AI response via email
        try:
            send_ai_email_response(sender_email, f"Re: {subject.replace('Re: ', '')}", ai_response)
            ai_message['sent'] = True
            ai_message['sent_timestamp'] = datetime.now().isoformat()
        except Exception as e:
            print(f"Error sending AI response: {e}")
            ai_message['sent'] = False
            ai_message['error'] = str(e)
    
    return conversation

def send_ai_email_response(recipient_email, subject, message_content):
    """Send AI-generated email response"""
    try:
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.set_content(message_content)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        print(f"✅ AI response sent to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending AI response: {e}")
        return False

# Routes
@app.route('/')
def index():
    return render_template('unified_dashboard.html')

@app.route('/api/analytics')
def get_analytics():
    """Get comprehensive email analytics"""
    analytics = calculate_analytics()
    return jsonify(analytics)

@app.route('/api/dashboard-stats')
def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    analytics = calculate_analytics()
    
    stats = {
        'total_emails_sent': analytics['total_sent'],
        'total_replies_received': analytics['total_replies'],
        'response_rate': f"{analytics['response_rate']}%",
        'ai_auto_replies': analytics['ai_auto_replies'],
        'manual_replies': analytics['manual_replies'],
        'success_rate': f"{(analytics['ai_auto_replies'] / max(analytics['total_replies'], 1) * 100):.1f}%"
    }
    
    return jsonify(stats)

@app.route('/get-contacts')
def get_contacts():
    """Get all contacts"""
    return jsonify(contacts)

@app.route('/api/contacts')
def get_contacts_api():
    """Get all contacts - API endpoint"""
    return jsonify(contacts)

@app.route('/add-contact', methods=['POST'])
def add_contact():
    """Add a single contact with simple validation"""
    global contacts
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if not email_addr or not first_name:
        return jsonify({'success': False, 'message': 'Email and first name required'})
    
    # Simple email format validation
    validation = validate_email_deliverability(email_addr)
    if not validation['valid']:
        return jsonify({'success': False, 'message': f'Invalid email format: {validation["reason"]}'})
    
    # Check if already exists
    for contact in contacts:
        if contact['email'].lower() == email_addr.lower():
            return jsonify({'success': False, 'message': 'Contact already exists'})
    
    new_contact = {
        'email': email_addr,
        'first_name': first_name,
        'last_name': last_name or '',
        'status': 'Pending'
    }
    
    contacts.append(new_contact)
    return jsonify({'success': True, 'message': 'Contact added successfully'})

@app.route('/api/add-contact', methods=['POST'])
def add_contact_api():
    """Add a single contact - API endpoint"""
    global contacts
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if not email_addr or not first_name:
        return jsonify({'success': False, 'message': 'Email and first name required'})
    
    # Check if already exists
    for contact in contacts:
        if contact['email'].lower() == email_addr.lower():
            return jsonify({'success': False, 'message': 'Contact already exists'})
    
    new_contact = {
        'email': email_addr,
        'first_name': first_name,
        'last_name': last_name or '',
        'status': 'Pending'
    }
    
    contacts.append(new_contact)
    return jsonify({'success': True, 'message': 'Contact added successfully'})

@app.route('/start-manual-campaign', methods=['POST'])
def start_campaign():
    """Start email campaign with real-time progress"""
    global contacts, sent_emails
    
    if not contacts:
        return jsonify({'success': False, 'message': 'No contacts added yet'})
    
    # Return immediately to allow real-time progress
    unsent_contacts = [c for c in contacts if c.get('status') != 'Sent']
    
    return jsonify({
        'success': True, 
        'message': f'Campaign started! Processing {len(unsent_contacts)} contacts.',
        'total_contacts': len(unsent_contacts)
    })

@app.route('/api/send-next-email', methods=['POST'])
def send_next_email():
    """Send next email in queue with real-time progress"""
    global contacts
    
    data = request.get_json()
    subject = data.get('subject', 'Your Email Campaign')
    message = data.get('message', 'Hello! This is our email campaign.')
    
    # Find next unsent contact
    next_contact = None
    contact_index = -1
    
    for i, contact in enumerate(contacts):
        if contact.get('status') != 'Sent' and contact.get('status') != 'Failed':
            next_contact = contact
            contact_index = i
            break
    
    if not next_contact:
        return jsonify({
            'success': True,
            'completed': True,
            'message': 'All emails processed!'
        })
    
    # Simple email validation
    print(f"📧 Sending to: {next_contact['email']}")
    validation_result = validate_email_deliverability(next_contact['email'])
    
    if not validation_result['valid']:
        next_contact['status'] = 'Failed'
        
        return jsonify({
            'success': True,
            'completed': False,
            'contact_index': contact_index,
            'contact_email': next_contact['email'],
            'contact_name': f"{next_contact['first_name']} {next_contact['last_name']}",
            'status': 'failed',
            'error': f'Invalid email format: {validation_result["reason"]}',
            'message': f'❌ Invalid email format: {next_contact["first_name"]}'
        })
    
    print(f"✅ Email format valid: {next_contact['email']}")
    
    try:
        # Create email
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = next_contact['email']
        msg['Subject'] = subject
        
        email_content = f"""Dear {next_contact['first_name']},

{message}

Best regards,
Your Team"""
        
        msg.set_content(email_content)
        
        # Send email
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL, PASSWORD)
                server.send_message(msg)
                
            # Mark as sent
            next_contact['status'] = 'Sent'
            next_contact['sent_date'] = datetime.now().isoformat()
            
            # Track email
            track_email_sent(next_contact['email'], subject, "Campaign")
            
            return jsonify({
                'success': True,
                'completed': False,
                'contact_index': contact_index,
                'contact_email': next_contact['email'],
                'contact_name': f"{next_contact['first_name']} {next_contact['last_name']}",
                'status': 'sent',
                'message': f'✅ Email sent to {next_contact["first_name"]}'
            })
            
        except Exception as e:
            next_contact['status'] = 'Failed'
            
            return jsonify({
                'success': True,
                'completed': False,
                'contact_index': contact_index,
                'contact_email': next_contact['email'],
                'contact_name': f"{next_contact['first_name']} {next_contact['last_name']}",
                'status': 'failed',
                'error': 'Send failed',
                'message': f'❌ Failed: {next_contact["first_name"]} - {str(e)[:50]}'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'completed': False,
            'message': f'Unexpected error: {str(e)}'
        })

@app.route('/api/status')
def get_status():
    """Get campaign status"""
    sent_count = len([c for c in contacts if c['status'] == 'Sent'])
    failed_count = len([c for c in contacts if c['status'] == 'Failed'])
    
    return jsonify({
        'running': False,
        'total_emails': len(contacts),
        'sent_emails': sent_count,
        'failed_emails': failed_count,
        'contacts': contacts
    })

@app.route('/api/replies')
def get_replies():
    """Get all replies"""
    return jsonify(replies)

@app.route('/api/email-monitoring/status')
def get_monitoring_status():
    """Get email monitoring status"""
    global email_monitoring_active, last_email_check
    
    return jsonify({
        'monitoring': email_monitoring_active,
        'status': 'active' if email_monitoring_active else 'inactive',
        'last_check': last_email_check.isoformat() if last_email_check else None,
        'total_replies': len(replies)
    })

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    try:
        start_email_monitoring()
        return jsonify({'success': True, 'message': 'Email monitoring started successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to start monitoring: {str(e)}'})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    try:
        stop_email_monitoring()
    return jsonify({'success': True, 'message': 'Email monitoring stopped'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to stop monitoring: {str(e)}'})

@app.route('/api/check-emails-now', methods=['POST'])
def check_emails_now():
    """Manually check for new emails"""
    try:
        new_replies = check_for_new_emails()
        return jsonify({
            'success': True, 
            'message': f'Email check completed. Found {new_replies} new replies.',
            'new_replies': new_replies,
            'total_replies': len(replies)
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error checking emails: {str(e)}'
        })

@app.route('/remove-contact', methods=['POST'])
def remove_contact():
    """Remove a contact"""
    global contacts
    
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    # Find and remove contact
    original_count = len(contacts)
    contacts = [c for c in contacts if c['email'].lower() != email.lower()]
    
    if len(contacts) < original_count:
        return jsonify({'success': True, 'message': 'Contact removed successfully'})
    else:
        return jsonify({'success': False, 'message': 'Contact not found'})

@app.route('/upload-bulk-contacts', methods=['POST'])
def upload_bulk_contacts():
    """Upload bulk contacts from Excel/CSV file"""
    global contacts
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    try:
        # Read the file based on extension
        if file.filename.endswith('.csv'):
            # Read CSV file
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file.read()))
        else:
            return jsonify({'success': False, 'message': 'Unsupported file format. Please upload CSV or Excel file.'})
        
        # Check required columns
        required_columns = ['Email', 'First Name', 'Last Name']
        if not all(col in df.columns for col in required_columns):
            return jsonify({
                'success': False, 
                'message': f'Missing required columns. Please include: {", ".join(required_columns)}'
            })
        
        # Process contacts
        added_count = 0
        duplicate_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                email = str(row['Email']).strip()
                first_name = str(row['First Name']).strip()
                last_name = str(row['Last Name']).strip()
                
                # Validate email format
                validation = validate_email_deliverability(email)
                if not validation['valid']:
                    error_count += 1
                    continue
                
                # Check for duplicates
                is_duplicate = any(contact['email'].lower() == email.lower() for contact in contacts)
                if is_duplicate:
                    duplicate_count += 1
                    continue
                
                # Add new contact
                new_contact = {
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'status': 'Pending'
                }
                
                contacts.append(new_contact)
                added_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error processing row {index}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Bulk upload completed! Added: {added_count}, Duplicates: {duplicate_count}, Errors: {error_count}',
            'added_count': added_count,
            'duplicate_count': duplicate_count,
            'error_count': error_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing file: {str(e)}'})

@app.route('/reset-campaign', methods=['POST'])
def reset_campaign():
    """Reset campaign status"""
    global contacts, sent_emails
    
    # Reset all contact statuses
    for contact in contacts:
        contact['status'] = 'Pending'
        if 'sent_date' in contact:
            del contact['sent_date']
    
    return jsonify({'success': True, 'message': 'Campaign reset successfully'})

@app.route('/api/send-ai-reply', methods=['POST'])
def send_ai_reply():
    """Send AI-generated reply"""
    data = request.get_json()
    reply_id = data.get('reply_id')
    
    if not reply_id:
        return jsonify({'success': False, 'message': 'Reply ID required'})
    
    # Find the original reply
    original_reply = None
    for reply in replies:
        if reply['id'] == reply_id:
            original_reply = reply
            break
    
    if not original_reply:
        return jsonify({'success': False, 'message': 'Reply not found'})
    
    # Generate AI response
    ai_response = generate_ai_reply(original_reply.get('content', ''), original_reply.get('from_name', ''))
    
    if not ai_response:
        return jsonify({'success': False, 'message': 'Failed to generate AI reply'})
    
    try:
        # Send the AI reply
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = original_reply['from_email']
        msg['Subject'] = f"Re: {original_reply['subject'].replace('Re: ', '')}"
        msg.set_content(ai_response)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Update reply data
        original_reply['ai_auto_replied'] = True
        original_reply['ai_reply_text'] = ai_response
        original_reply['ai_reply_date'] = datetime.now().isoformat()
        
        # Update analytics
        email_analytics['ai_auto_replies'] += 1
        
        return jsonify({'success': True, 'message': 'AI reply sent successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error sending reply: {str(e)}'})

# Fake email and bounce detection routes removed

@app.route('/api/validate-email', methods=['POST'])
def validate_single_email():
    """Validate a single email address"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    validation = validate_email_deliverability(email)
        
        return jsonify({
            'success': True, 
        'valid': validation['valid'],
        'reason': validation['reason'],
        'email': email
    })

@app.route('/api/email-stats')
def get_email_stats():
    """Get email statistics"""
    total_contacts = len(contacts)
    sent_count = len([c for c in contacts if c.get('status') == 'Sent'])
    
    return jsonify({
        'total_contacts': total_contacts,
        'valid_emails': total_contacts,
        'fake_emails': 0,
        'bounced_emails': 0,
        'sent_emails': sent_count,
        'validation_rate': 100
    })

@app.route('/api/reset-all-data', methods=['POST'])
def reset_all_data():
    """Reset all data"""
    global contacts, sent_emails, replies, conversations, unanswered_emails
    
    contacts = []
    sent_emails = []
    replies = []
    conversations = []
    unanswered_emails = []
    
    return jsonify({
        'success': True,
        'message': 'All data reset successfully'
    })

@app.route('/api/email-limits')
def get_email_limits():
    """Get email sending limits status"""
    status = get_email_limits_status()
    return jsonify(status)

@app.route('/api/update-email-limits', methods=['POST'])
def update_email_limits():
    """Update email sending limits"""
    global DAILY_EMAIL_LIMIT, HOURLY_EMAIL_LIMIT, EMAIL_SENDING_COOLDOWN
    
    data = request.get_json()
    
    if 'daily_limit' in data:
        DAILY_EMAIL_LIMIT = max(1, min(1000, data['daily_limit']))
    if 'hourly_limit' in data:
        HOURLY_EMAIL_LIMIT = max(1, min(100, data['hourly_limit']))
    if 'cooldown' in data:
        EMAIL_SENDING_COOLDOWN = max(0, min(60, data['cooldown']))
    
    return jsonify({
        'success': True,
        'message': 'Email limits updated successfully',
        'limits': {
            'daily_limit': DAILY_EMAIL_LIMIT,
            'hourly_limit': HOURLY_EMAIL_LIMIT,
            'cooldown_seconds': EMAIL_SENDING_COOLDOWN
        }
    })

# Bounce detection routes removed - simplified system

# New AI Conversation and Reply Tracking Routes

@app.route('/api/conversations')
def get_conversations():
    """Get all AI conversations"""
    return jsonify(conversations)

@app.route('/api/conversation/<int:conversation_id>')
def get_conversation(conversation_id):
    """Get specific conversation by ID"""
    conversation = None
    for conv in conversations:
        if conv['id'] == conversation_id:
            conversation = conv
            break
    
    if conversation:
        return jsonify(conversation)
    else:
        return jsonify({'error': 'Conversation not found'}), 404

@app.route('/api/unanswered-emails')
def get_unanswered_emails():
    """Get all unanswered emails"""
    # Update days since sent
    for email in unanswered_emails:
        sent_date = datetime.fromisoformat(email['sent_date'])
        days_diff = (datetime.now() - sent_date).days
        email['days_since_sent'] = days_diff
    
    return jsonify(unanswered_emails)

# Demo simulation endpoint removed for production

@app.route('/api/send-manual-reply', methods=['POST'])
def send_manual_reply():
    """Send manual reply to a conversation"""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    message_content = data.get('message')
    
    if not conversation_id or not message_content:
        return jsonify({'success': False, 'message': 'Conversation ID and message required'})
    
    # Find conversation
    conversation = None
    for conv in conversations:
        if conv['id'] == conversation_id:
            conversation = conv
            break
    
    if not conversation:
        return jsonify({'success': False, 'message': 'Conversation not found'})
    
    # Add manual message to conversation
    manual_message = {
        'id': len(conversation['messages']) + 1,
        'sender_type': 'human',
        'sender_name': 'Human Agent',
        'content': message_content,
        'timestamp': datetime.now().isoformat(),
        'subject': f"Re: {conversation['messages'][-1]['subject'].replace('Re: ', '')}"
    }
    conversation['messages'].append(manual_message)
    conversation['message_count'] += 1
    conversation['last_activity'] = datetime.now().isoformat()
    
    # Send manual response via email
    try:
        success = send_ai_email_response(
            conversation['customer_email'], 
            manual_message['subject'], 
            message_content
        )
        
        if success:
            manual_message['sent'] = True
            manual_message['sent_timestamp'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Manual reply sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send manual reply'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error sending manual reply: {str(e)}'})

@app.route('/api/conversation-stats')
def get_conversation_stats():
    """Get conversation statistics"""
    total_conversations = len(conversations)
    active_conversations = len([c for c in conversations if c['status'] == 'active'])
    total_messages = sum(c['message_count'] for c in conversations)
    
    # Calculate response rate
    replied_emails = len([e for e in sent_emails if e.get('replied', False)])
    total_sent = len(sent_emails)
    response_rate = (replied_emails / max(total_sent, 1)) * 100
    
    return jsonify({
        'total_conversations': total_conversations,
        'active_conversations': active_conversations,
        'total_messages': total_messages,
        'unanswered_emails': len(unanswered_emails),
        'response_rate': round(response_rate, 2),
        'ai_responses_sent': sum(len([m for m in c['messages'] if m['sender_type'] == 'ai']) for c in conversations)
    })

# Production configuration for Vercel
def create_app():
    """Create Flask app for production deployment"""
    # Start email monitoring automatically
    try:
        start_email_monitoring()
        print("📧 Email monitoring started automatically")
    except Exception as e:
        print(f"⚠️  Could not start email monitoring: {str(e)}")
    
    return app

# For local development
if __name__ == '__main__':
    print("🚀 Starting AI Email Campaign Manager...")
    print(f"📧 Email: {EMAIL}")
    print(f"🤖 AI: {'Configured' if GEMINI_API_KEY else 'Not configured'}")
    print("🌐 Server starting on http://localhost:5008")
    print("=" * 50)
    
    # Start email monitoring automatically
    try:
        start_email_monitoring()
        print("📧 Email monitoring started automatically")
    except Exception as e:
        print(f"⚠️  Could not start email monitoring: {str(e)}")
    
    app.run(debug=False, host='0.0.0.0', port=5008)
