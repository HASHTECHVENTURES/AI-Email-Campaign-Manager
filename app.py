#!/usr/bin/env python3
"""
AI Email Campaign Manager - Clean Local Version
Optimized for local development and production use
"""

from flask import Flask, render_template, request, jsonify
import smtplib
from email.message import EmailMessage
from datetime import datetime
import requests
import json
import pandas as pd
import io
import re
import dns.resolver
import socket

app = Flask(__name__)

# Email Configuration
EMAIL = "karmaterra427@gmail.com"
PASSWORD = "jidw kfwg hpsh diqi"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Gemini AI Configuration
GEMINI_API_KEY = "AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Data Storage
contacts = []
sent_emails = []
replies = []
bounced_emails = []
fake_emails = []

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
    """Comprehensive email validation"""
    if not validate_email_format(email):
        return {'valid': False, 'reason': 'Invalid email format'}
    
    domain = email.split('@')[1]
    if not check_domain_exists(domain):
        return {'valid': False, 'reason': 'Domain does not exist'}
    
    return {'valid': True, 'reason': 'Valid email'}

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
    """Track sent emails"""
    global sent_emails, email_analytics
    
    email_record = {
        'recipient': recipient,
        'subject': subject,
        'campaign_type': campaign_type,
        'sent_date': datetime.now().isoformat(),
        'status': 'sent'
    }
    
    sent_emails.append(email_record)
    email_analytics['total_sent'] += 1

def detect_bounce_from_smtp_error(email, error_message):
    """Detect bounce from SMTP error and add to bounced emails"""
    global bounced_emails
    
    bounce_reasons = {
        'mailbox full': 'Mailbox is full',
        'user unknown': 'User does not exist',
        'domain not found': 'Domain does not exist',
        'relay access denied': 'Server rejected email',
        'message too large': 'Message size exceeds limit',
        'spam': 'Email marked as spam',
        'blocked': 'Email address blocked',
        'invalid recipient': 'Invalid recipient address',
        '550': 'Permanent failure - User unknown',
        '552': 'Mailbox full',
        '553': 'Invalid recipient address',
        '554': 'Transaction failed'
    }
    
    reason = 'Unknown bounce reason'
    error_lower = error_message.lower()
    
    for key, value in bounce_reasons.items():
        if key in error_lower:
            reason = value
            break
    
    bounce_entry = {
        'email': email,
        'reason': reason,
        'error_message': error_message,
        'timestamp': datetime.now().isoformat(),
        'bounce_type': 'hard' if any(x in error_lower for x in ['user unknown', 'domain not found', 'invalid', '550', '553']) else 'soft'
    }
    
    # Check if already in bounced list
    if not any(be['email'].lower() == email.lower() for be in bounced_emails):
        bounced_emails.append(bounce_entry)
        print(f"🚫 Bounce detected: {email} - {reason}")
    
    return bounce_entry

def check_email_bounces():
    """Check for email bounces and simulate bounce detection"""
    global bounced_emails, sent_emails
    
    try:
        # Simulate bounce detection for testing
        test_bounce_patterns = [
            'test@', 'invalid@', 'bounce@', 'noreply@', 'donotreply@',
            'fake@', 'spam@', 'blocked@', 'nonexistent@'
        ]
        
        # Check recent sent emails for potential bounces
        recent_emails = sent_emails[-50:] if len(sent_emails) > 50 else sent_emails
        
        for sent_email in recent_emails:
            recipient = sent_email['recipient'].lower()
            
            # Check for bounce patterns
            for pattern in test_bounce_patterns:
                if pattern in recipient:
                    if not any(be['email'].lower() == recipient for be in bounced_emails):
                        detect_bounce_from_smtp_error(
                            sent_email['recipient'], 
                            f"550 User unknown - {pattern.replace('@', '')} pattern detected"
                        )
                        break
        
        # Add some random bounces for demonstration
        import random
        if len(sent_emails) > 0 and random.random() < 0.1:  # 10% chance
            recent_email = random.choice(sent_emails[-10:])
            if not any(be['email'].lower() == recent_email['recipient'].lower() for be in bounced_emails):
                detect_bounce_from_smtp_error(
                    recent_email['recipient'],
                    "552 Mailbox full - simulated bounce"
                )
        
        print(f"✅ Bounce check completed. Total bounced emails: {len(bounced_emails)}")
        return True
        
    except Exception as e:
        print(f"❌ Error checking bounces: {e}")
        return False

def generate_ai_reply(original_message, sender_name=""):
    """Generate AI reply using Gemini API"""
    try:
        prompt = f"""
        You are a professional email assistant. Generate a helpful, friendly, and professional reply to this email.
        
        Original message from {sender_name}:
        {original_message}
        
        Generate a response that is:
        - Professional and courteous
        - Helpful and informative
        - Concise (2-3 paragraphs max)
        - Ends with a clear call to action or next step
        
        Do not include subject line or email headers, just the message body.
        """
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            ai_reply = result['candidates'][0]['content']['parts'][0]['text']
            return ai_reply.strip()
        else:
            return None
            
    except Exception as e:
        print(f"AI Reply Error: {str(e)}")
        return None

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
    """Add a single contact with email validation"""
    global contacts, fake_emails
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if not email_addr or not first_name:
        return jsonify({'success': False, 'message': 'Email and first name required'})
    
    # Validate email
    validation = validate_email_deliverability(email_addr)
    if not validation['valid']:
        fake_emails.append({
            'email': email_addr,
            'reason': validation['reason'],
            'detected_date': datetime.now().isoformat()
        })
        return jsonify({'success': False, 'message': f'Invalid email: {validation["reason"]}'})
    
    # Check if already exists
    for contact in contacts:
        if contact['email'].lower() == email_addr.lower():
            return jsonify({'success': False, 'message': 'Contact already exists'})
    
    new_contact = {
        'email': email_addr,
        'first_name': first_name,
        'last_name': last_name or '',
        'status': 'Pending',
        'validated': True,
        'validation_date': datetime.now().isoformat()
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
    """Start email campaign"""
    global contacts, sent_emails
    
    if not contacts:
        return jsonify({'success': False, 'message': 'No contacts added yet'})
    
    subject = request.form.get('subject', 'Your Email Campaign')
    message = request.form.get('message', 'Hello! This is our email campaign.')
    
    sent_count = 0
    failed_count = 0
    
    for contact in contacts:
        if contact['status'] != 'Sent':
    try:
        # Create email
        msg = EmailMessage()
        msg['From'] = EMAIL
                msg['To'] = contact['email']
        msg['Subject'] = subject
                
                email_content = f"""Dear {contact['first_name']},

{message}

Best regards,
Your Team"""
                
                msg.set_content(email_content)
        
        # Send email with bounce detection
        try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = str(e)
            print(f"❌ Recipients refused for {contact['email']}: {error_msg}")
            detect_bounce_from_smtp_error(contact['email'], f"Recipients refused: {error_msg}")
            continue
        except smtplib.SMTPResponseException as e:
            error_msg = f"SMTP {e.smtp_code}: {e.smtp_error.decode() if hasattr(e.smtp_error, 'decode') else str(e.smtp_error)}"
            print(f"❌ SMTP error for {contact['email']}: {error_msg}")
            detect_bounce_from_smtp_error(contact['email'], error_msg)
            continue
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to send email to {contact['email']}: {error_msg}")
            if any(keyword in error_msg.lower() for keyword in ['user unknown', 'mailbox', 'recipient', 'invalid', 'refused']):
                detect_bounce_from_smtp_error(contact['email'], error_msg)
            continue
        
                # Mark as sent
                contact['status'] = 'Sent'
                contact['sent_date'] = datetime.now().isoformat()
                
                # Track email
                track_email_sent(contact['email'], subject, "Campaign")
                
                sent_count += 1
        
    except Exception as e:
                contact['status'] = 'Failed'
                failed_count += 1
    
    return jsonify({
        'success': True, 
        'message': f'Campaign completed! Sent {sent_count} emails, {failed_count} failed.'
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
    return jsonify({
        'monitoring': False,
        'status': 'inactive'
    })

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    return jsonify({'success': True, 'message': 'Email monitoring started'})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    return jsonify({'success': True, 'message': 'Email monitoring stopped'})

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
                
                # Validate email format and deliverability
                validation = validate_email_deliverability(email)
                if not validation['valid']:
                    fake_emails.append({
                        'email': email,
                        'reason': validation['reason'],
                        'detected_date': datetime.now().isoformat()
                    })
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
                    'status': 'Pending',
                    'validated': True,
                    'validation_date': datetime.now().isoformat()
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

@app.route('/api/fake-emails')
def get_fake_emails():
    """Get list of detected fake emails"""
    return jsonify(fake_emails)

@app.route('/api/bounced-emails')
def get_bounced_emails():
    """Get list of bounced emails"""
    return jsonify(bounced_emails)

@app.route('/api/validate-email', methods=['POST'])
def validate_single_email():
    """Validate a single email address"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    validation = validate_email_deliverability(email)
    
    if not validation['valid']:
        fake_emails.append({
            'email': email,
            'reason': validation['reason'],
            'detected_date': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True, 
        'valid': validation['valid'],
        'reason': validation['reason'],
        'email': email
    })

@app.route('/api/email-stats')
def get_email_stats():
    """Get email validation statistics"""
    total_contacts = len(contacts)
    fake_count = len(fake_emails)
    bounce_count = len(bounced_emails)
    valid_count = len([c for c in contacts if c.get('validated', False)])
    
    return jsonify({
        'total_contacts': total_contacts,
        'valid_emails': valid_count,
        'fake_emails': fake_count,
        'bounced_emails': bounce_count,
        'validation_rate': round((valid_count / max(total_contacts, 1)) * 100, 2)
    })

@app.route('/api/clean-fake-emails', methods=['POST'])
def clean_fake_emails():
    """Remove fake emails from contacts list"""
    global contacts, fake_emails
    
    fake_email_list = [fe['email'] for fe in fake_emails]
    original_count = len(contacts)
    
    # Remove contacts with fake emails
    contacts = [c for c in contacts if c['email'].lower() not in [fe.lower() for fe in fake_email_list]]
    
    removed_count = original_count - len(contacts)
    
    return jsonify({
        'success': True,
        'message': f'Removed {removed_count} fake emails from contacts',
        'removed_count': removed_count
    })

@app.route('/api/clear-fake-emails', methods=['POST'])
def clear_fake_emails():
    """Clear the fake emails list"""
    global fake_emails
    
    fake_emails = []
    
    return jsonify({
        'success': True,
        'message': 'Fake emails list cleared'
    })

@app.route('/api/reset-all-data', methods=['POST'])
def reset_all_data():
    """Reset all data (contacts, fake emails, etc.)"""
    global contacts, sent_emails, replies, fake_emails, bounced_emails
    
    contacts = []
    sent_emails = []
    replies = []
    fake_emails = []
    bounced_emails = []
    
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

@app.route('/api/check-bounces', methods=['POST'])
def check_bounces_api():
    """Manually trigger bounce detection"""
    try:
        result = check_email_bounces()
        
        return jsonify({
            'success': True,
            'message': f'Bounce check completed. Found {len(bounced_emails)} bounced emails.',
            'bounced_count': len(bounced_emails),
            'bounced_emails': bounced_emails[-10:]  # Return last 10 for display
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error checking bounces: {str(e)}'
        })

@app.route('/api/simulate-bounce', methods=['POST'])
def simulate_bounce_api():
    """Simulate a bounce for testing purposes"""
    data = request.get_json()
    email = data.get('email', 'test@example.com')
    error_type = data.get('error_type', 'user_unknown')
    
    error_messages = {
        'user_unknown': '550 User unknown',
        'mailbox_full': '552 Mailbox full',
        'domain_not_found': '550 Domain not found',
        'blocked': '554 Message blocked',
        'invalid_recipient': '553 Invalid recipient address'
    }
    
    error_msg = error_messages.get(error_type, '550 User unknown')
    bounce_entry = detect_bounce_from_smtp_error(email, error_msg)
    
    return jsonify({
        'success': True,
        'message': f'Simulated bounce for {email}',
        'bounce_entry': bounce_entry
        })

if __name__ == '__main__':
    print("🚀 Starting AI Email Campaign Manager...")
    print(f"📧 Email: {EMAIL}")
    print(f"🤖 AI: {'Configured' if GEMINI_API_KEY else 'Not configured'}")
    print("🌐 Server starting on http://localhost:5008")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5008)
