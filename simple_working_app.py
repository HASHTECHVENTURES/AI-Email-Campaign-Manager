#!/usr/bin/env python3
# 🤖 AI EMAIL AUTOMATION SYSTEM - MAIN APPLICATION
# Enhanced with comprehensive tracking and Gemini AI integration

from flask import Flask, render_template, request, jsonify
import smtplib
from email.message import EmailMessage
import imaplib
import email
import re
from datetime import datetime
import threading
import time
import requests
import json

app = Flask(__name__)

# SIMPLE EMAIL CONFIGURATION - GUARANTEED TO WORK
EMAIL = "karmaterra427@gmail.com"
PASSWORD = "jidw kfwg hpsh diqi"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# GEMINI AI CONFIGURATION
GEMINI_API_KEY = "AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ENHANCED DATA STORAGE WITH ANALYTICS
contacts = []
sent_emails = []
replies = []
monitoring_active = False

# 📊 COMPREHENSIVE EMAIL ANALYTICS
email_analytics = {
    'total_sent': 0,
    'total_replies': 0,
    'response_rate': 0.0,
    'avg_response_time_hours': 0,
    'campaigns_today': 0,
    'ai_auto_replies': 0,
    'manual_replies': 0,
    'conversation_threads': {},
    'daily_stats': {},
    'best_response_times': [],
    'engagement_metrics': {
        'positive_responses': 0,
        'neutral_responses': 0,
        'negative_responses': 0
    }
}

# 📊 ANALYTICS FUNCTIONS
def calculate_analytics():
    """Calculate comprehensive email analytics"""
    global email_analytics, sent_emails, replies
    
    # Basic metrics
    email_analytics['total_sent'] = len(sent_emails)
    email_analytics['total_replies'] = len(replies)
    
    # Response rate calculation
    if email_analytics['total_sent'] > 0:
        email_analytics['response_rate'] = round((email_analytics['total_replies'] / email_analytics['total_sent']) * 100, 2)
    else:
        email_analytics['response_rate'] = 0.0
    
    # Calculate average response time
    response_times = []
    for reply in replies:
        # Find corresponding sent email
        reply_email = reply.get('from_email', '').lower()
        for sent in sent_emails:
            if sent.get('recipient', '').lower() == reply_email:
                try:
                    sent_time = datetime.fromisoformat(sent.get('sent_date', ''))
                    reply_time = datetime.fromisoformat(reply.get('timestamp', ''))
                    diff_hours = (reply_time - sent_time).total_seconds() / 3600
                    response_times.append(diff_hours)
                    break
                except:
                    continue
    
    if response_times:
        email_analytics['avg_response_time_hours'] = round(sum(response_times) / len(response_times), 2)
        email_analytics['best_response_times'] = sorted(response_times)[:5]  # Top 5 fastest
    
    # Count AI vs Manual replies
    email_analytics['ai_auto_replies'] = sum(1 for r in replies if r.get('ai_auto_replied', False))
    email_analytics['manual_replies'] = sum(1 for r in replies if r.get('manual_reply_sent', False))
    
    # Daily stats
    today = datetime.now().strftime('%Y-%m-%d')
    email_analytics['campaigns_today'] = sum(1 for s in sent_emails if s.get('sent_date', '').startswith(today))
    
    return email_analytics

def track_email_sent(recipient, subject, campaign_type="Manual"):
    """Enhanced email tracking"""
    global sent_emails, email_analytics
    
    email_record = {
        'recipient': recipient,
        'subject': subject,
        'campaign_type': campaign_type,
        'sent_date': datetime.now().isoformat(),
        'status': 'sent'
    }
    
    sent_emails.append(email_record)
    
    # Update analytics
    email_analytics['total_sent'] += 1
    
    # Update daily stats
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in email_analytics['daily_stats']:
        email_analytics['daily_stats'][today] = {'sent': 0, 'replies': 0}
    email_analytics['daily_stats'][today]['sent'] += 1
    
    print(f"📊 TRACKED EMAIL: {recipient} | Total Sent: {email_analytics['total_sent']}")

def track_reply_received(reply_data):
    """Enhanced reply tracking"""
    global email_analytics
    
    # Update analytics
    email_analytics['total_replies'] += 1
    
    # Update daily stats
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in email_analytics['daily_stats']:
        email_analytics['daily_stats'][today] = {'sent': 0, 'replies': 0}
    email_analytics['daily_stats'][today]['replies'] += 1
    
    # Recalculate response rate
    calculate_analytics()
    
    print(f"📈 TRACKED REPLY: {reply_data.get('from_email')} | Total Replies: {email_analytics['total_replies']}")

# 🤖 GEMINI AI FUNCTIONS
def generate_ai_reply(original_message, sender_name=""):
    """Generate AI reply using Gemini API"""
    try:
        # Prepare the prompt for Gemini
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
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        
        print(f"🤖 GENERATING AI REPLY for {sender_name}...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            ai_reply = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ AI REPLY GENERATED: {len(ai_reply)} characters")
            return ai_reply.strip()
        else:
            print(f"❌ GEMINI API ERROR: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ AI REPLY ERROR: {str(e)}")
        return None

def send_ai_auto_reply(reply_data):
    """Send automatic AI reply"""
    try:
        # Generate AI response
        ai_response = generate_ai_reply(reply_data['content'], reply_data.get('from_name', ''))
        
        if not ai_response:
            print(f"❌ FAILED to generate AI reply for {reply_data['from_email']}")
            return False
        
        # Send the AI reply
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = reply_data['from_email']
        msg['Subject'] = f"Re: {reply_data['subject'].replace('Re: ', '')}"
        msg.set_content(ai_response)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Update reply data
        reply_data['ai_auto_replied'] = True
        reply_data['ai_reply_text'] = ai_response
        reply_data['ai_reply_date'] = datetime.now().isoformat()
        
        # Update analytics
        email_analytics['ai_auto_replies'] += 1
        
        print(f"🤖✅ AI AUTO-REPLY SENT TO: {reply_data['from_email']}")
        return True
        
    except Exception as e:
        print(f"❌ AI AUTO-REPLY FAILED: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template('unified_dashboard.html')

@app.route('/api/analytics')
def get_analytics():
    """Get comprehensive email analytics"""
    analytics = calculate_analytics()
    print(f"📊 ANALYTICS REQUEST: {analytics['response_rate']}% response rate")
    return jsonify(analytics)

@app.route('/api/dashboard-stats')
def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    analytics = calculate_analytics()
    
    # Enhanced stats for dashboard
    stats = {
        'total_emails_sent': analytics['total_sent'],
        'total_replies_received': analytics['total_replies'],
        'response_rate': f"{analytics['response_rate']}%",
        'avg_response_time': f"{analytics['avg_response_time_hours']:.1f} hours",
        'campaigns_today': analytics['campaigns_today'],
        'ai_auto_replies': analytics['ai_auto_replies'],
        'manual_replies': analytics['manual_replies'],
        'success_rate': f"{(analytics['ai_auto_replies'] / max(analytics['total_replies'], 1) * 100):.1f}%",
        'daily_stats': analytics['daily_stats']
    }
    
    return jsonify(stats)

@app.route('/get-contacts')
def get_contacts():
    """Get all contacts"""
    print(f"📋 GET CONTACTS: {len(contacts)} contacts")
    return jsonify(contacts)

@app.route('/api/contacts')
def get_contacts_api():
    """Get all contacts - API endpoint"""
    print(f"📋 GET CONTACTS API: {len(contacts)} contacts")
    return jsonify(contacts)

@app.route('/add-contact', methods=['POST'])
def add_contact():
    """Add a single contact"""
    global contacts
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    print(f"➕ ADDING CONTACT: {email_addr} - {first_name} {last_name}")
    
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
    print(f"✅ CONTACT ADDED: Total contacts now: {len(contacts)}")
    
    return jsonify({'success': True, 'message': 'Contact added successfully'})

@app.route('/api/add-contact', methods=['POST'])
def add_contact_api():
    """Add a single contact - API endpoint"""
    global contacts
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    print(f"➕ ADDING CONTACT API: {email_addr} - {first_name} {last_name}")
    
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
    print(f"✅ CONTACT ADDED API: Total contacts now: {len(contacts)}")
    
    return jsonify({'success': True, 'message': 'Contact added successfully'})

@app.route('/start-manual-campaign', methods=['POST'])
def start_campaign():
    """Start email campaign"""
    global contacts, sent_emails
    
    print(f"🚀 STARTING CAMPAIGN with {len(contacts)} contacts")
    
    if not contacts:
        return jsonify({'success': False, 'message': 'No contacts added yet'})
    
    subject = request.form.get('subject', 'Your Email Campaign')
    message = request.form.get('message', 'Hello! This is our email campaign.')
    
    sent_count = 0
    failed_count = 0
    
    for contact in contacts:
        if contact['status'] != 'Sent':
            try:
                print(f"📧 SENDING EMAIL TO: {contact['email']}")
                
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
                
                # Send email
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(EMAIL, PASSWORD)
                    server.send_message(msg)
                
                # Mark as sent
                contact['status'] = 'Sent'
                contact['sent_date'] = datetime.now().isoformat()
                
                # Enhanced email tracking
                track_email_sent(contact['email'], subject, "Campaign")
                
                sent_count += 1
                print(f"✅ EMAIL SENT TO: {contact['email']}")
                print(f"📊 SENT COUNT NOW: {sent_count}")
                print(f"📋 TOTAL SENT EMAILS: {len(sent_emails)}")
                
                # Force update contact status immediately
                print(f"🔧 CONTACT STATUS: {contact['email']} = {contact['status']}")
                
            except Exception as e:
                print(f"❌ EMAIL FAILED TO: {contact['email']} - {str(e)}")
                contact['status'] = 'Failed'
                failed_count += 1
    
    print(f"📊 CAMPAIGN COMPLETE: {sent_count} sent, {failed_count} failed")
    return jsonify({
        'success': True, 
        'message': f'Campaign completed! Sent {sent_count} emails, {failed_count} failed.'
    })

@app.route('/api/status')
def get_status():
    """Get campaign status"""
    sent_count = len([c for c in contacts if c['status'] == 'Sent'])
    failed_count = len([c for c in contacts if c['status'] == 'Failed'])
    
    print(f"📊 STATUS DEBUG:")
    print(f"   Total contacts: {len(contacts)}")
    print(f"   Sent count: {sent_count}")
    print(f"   Failed count: {failed_count}")
    print(f"   Sent emails tracked: {len(sent_emails)}")
    
    for i, contact in enumerate(contacts):
        print(f"   Contact {i+1}: {contact['email']} = {contact['status']}")
    
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
    print(f"📬 GET REPLIES: {len(replies)} replies")
    return jsonify(replies)

@app.route('/api/send-ai-reply', methods=['POST'])
def send_ai_reply():
    """Send AI-generated reply to a specific email"""
    global replies
    
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
    
    # Check if already replied
    if original_reply.get('ai_auto_replied') or original_reply.get('manual_reply_sent'):
        return jsonify({'success': False, 'message': 'Already replied to this email'})
    
    # Send AI auto-reply
    success = send_ai_auto_reply(original_reply)
    
    if success:
        return jsonify({'success': True, 'message': 'AI reply sent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send AI reply'})

@app.route('/api/send-manual-reply', methods=['POST'])
def send_manual_reply():
    """Send a manual reply to a specific email"""
    global replies
    
    data = request.get_json()
    reply_id = data.get('reply_id')
    reply_text = data.get('reply_text')
    
    if not reply_id or not reply_text:
        return jsonify({'success': False, 'message': 'Reply ID and text required'})
    
    # Find the original reply
    original_reply = None
    for reply in replies:
        if reply['id'] == reply_id:
            original_reply = reply
            break
    
    if not original_reply:
        return jsonify({'success': False, 'message': 'Reply not found'})
    
    try:
        print(f"📤 SENDING MANUAL REPLY TO: {original_reply['from_email']}")
        
        # Create reply email
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = original_reply['from_email']
        msg['Subject'] = f"Re: {original_reply['subject'].replace('Re: ', '')}"
        msg.set_content(reply_text)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Mark as manually replied
        original_reply['manual_reply_sent'] = True
        original_reply['manual_reply_text'] = reply_text
        original_reply['manual_reply_date'] = datetime.now().isoformat()
        
        # Update analytics
        email_analytics['manual_replies'] += 1
        
        print(f"✅ MANUAL REPLY SENT TO: {original_reply['from_email']}")
        print(f"📊 MANUAL REPLIES: {email_analytics['manual_replies']}")
        
        return jsonify({'success': True, 'message': 'Manual reply sent successfully'})
        
    except Exception as e:
        print(f"❌ MANUAL REPLY FAILED TO: {original_reply['from_email']} - {str(e)}")
        return jsonify({'success': False, 'message': f'Error sending reply: {str(e)}'})

@app.route('/api/email-monitoring/status')
def get_monitoring_status():
    """Get email monitoring status"""
    return jsonify({
        'monitoring': monitoring_active,
        'status': 'active' if monitoring_active else 'inactive'
    })

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    global monitoring_active
    monitoring_active = True
    print("📧 EMAIL MONITORING STARTED")
    return jsonify({'success': True, 'message': 'Email monitoring started'})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    global monitoring_active
    monitoring_active = False
    print("📧 EMAIL MONITORING STOPPED")
    return jsonify({'success': True, 'message': 'Email monitoring stopped'})

# Additional endpoints that the frontend expects
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
        print(f"🗑️ CONTACT REMOVED: {email}")
        return jsonify({'success': True, 'message': 'Contact removed successfully'})
    else:
        return jsonify({'success': False, 'message': 'Contact not found'})

@app.route('/upload-bulk-contacts', methods=['POST'])
def upload_bulk_contacts():
    """Upload bulk contacts from file"""
    # For now, return a simple response since file upload is complex
    return jsonify({'success': False, 'message': 'Bulk upload not implemented yet'})

@app.route('/reset-campaign', methods=['POST'])
def reset_campaign():
    """Reset campaign status"""
    global contacts, sent_emails
    
    # Reset all contact statuses
    for contact in contacts:
        contact['status'] = 'Pending'
        if 'sent_date' in contact:
            del contact['sent_date']
    
    print("🔄 CAMPAIGN RESET")
    return jsonify({'success': True, 'message': 'Campaign reset successfully'})

@app.route('/api/analytics/dashboard')
def get_analytics_dashboard():
    """Get analytics data"""
    sent_count = len([c for c in contacts if c['status'] == 'Sent'])
    failed_count = len([c for c in contacts if c['status'] == 'Failed'])
    reply_count = len(replies)
    
    return jsonify({
        'total_contacts': len(contacts),
        'sent_emails': sent_count,
        'failed_emails': failed_count,
        'replies': reply_count,
        'success_rate': round((sent_count / len(contacts) * 100) if contacts else 0, 1)
    })

@app.route('/api/email-accounts')
def get_email_accounts():
    """Get email accounts"""
    return jsonify([{
        'id': 1,
        'email': EMAIL,
        'name': 'Primary Account',
        'status': 'active',
        'is_default': True
    }])

@app.route('/api/replies/remove-duplicates', methods=['POST'])
def remove_duplicates():
    """Remove duplicate replies"""
    global replies
    
    original_count = len(replies)
    seen_emails = set()
    unique_replies = []
    
    for reply in replies:
        email_key = f"{reply['from_email']}_{reply['subject']}"
        if email_key not in seen_emails:
            seen_emails.add(email_key)
            unique_replies.append(reply)
    
    removed_count = original_count - len(unique_replies)
    replies = unique_replies
    
    print(f"🗑️ REMOVED {removed_count} DUPLICATE REPLIES")
    
    return jsonify({
        'success': True,
        'removed_count': removed_count,
        'original_count': original_count,
        'current_count': len(replies)
    })

@app.route('/api/replies/clear', methods=['POST'])
def clear_replies():
    """Clear all replies"""
    global replies
    replies = []
    print("🗑️ ALL REPLIES CLEARED")
    return jsonify({'success': True, 'message': 'All replies cleared'})

@app.route('/api/email-monitoring/check-now', methods=['POST'])
def check_replies():
    """Check for replies manually"""
    global replies
    
    print(f"🔍 CHECKING FOR REPLIES...")
    
    if not sent_emails:
        return jsonify({'success': False, 'message': 'No sent emails found. Send a campaign first.'})
    
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        
        # Search for recent emails - get ALL emails from today
        from datetime import date
        today = date.today().strftime('%d-%b-%Y')
        print(f"🔍 SEARCHING FOR EMAILS FROM: {today}")
        
        # Search for emails from today
        _, message_numbers = mail.search(None, f'SINCE {today}')
        if message_numbers[0]:
            message_numbers = message_numbers[0].split()
            print(f"📬 FOUND {len(message_numbers)} EMAILS FROM TODAY")
        else:
            # Fallback to last 20 emails if no emails today
            _, message_numbers = mail.search(None, 'ALL')
            message_numbers = message_numbers[0].split()[-20:]  # Last 20 emails
            print(f"📬 FALLBACK: CHECKING LAST {len(message_numbers)} EMAILS")
        
        new_replies = 0
        
        for num in message_numbers:
            _, msg_data = mail.fetch(num, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            from_email = email_message['From']
            subject = email_message['Subject'] or ''
            
            # Extract email address
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_email)
            if email_match:
                sender_email = email_match.group()
                print(f"📧 CHECKING EMAIL FROM: {sender_email}")
                
                # Check if this is from someone we sent emails to
                sent_to_this_person = any(sent['recipient'].lower() == sender_email.lower() for sent in sent_emails)
                print(f"🔍 SENT TO THIS PERSON: {sent_to_this_person}")
                
                if sent_to_this_person:
                    # Check if we already have this reply (check by email AND subject)
                    existing_reply = any(
                        r['from_email'].lower() == sender_email.lower() and 
                        r['subject'] == subject 
                        for r in replies
                    )
                    print(f"🔍 EXISTING REPLY: {existing_reply}")
                    
                    if not existing_reply:
                        # Get email content
                        content = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        # Add reply
                        reply = {
                            'id': len(replies) + 1,
                            'from_email': sender_email,
                            'from_name': from_email.split('<')[0].strip() if '<' in from_email else sender_email,
                            'subject': subject,
                            'content': content[:500],  # First 500 chars
                            'timestamp': datetime.now().isoformat(),
                            'ai_auto_replied': False
                        }
                        
                        replies.append(reply)
                        new_replies += 1
                        
                        # Enhanced reply tracking
                        track_reply_received(reply)
                        
                        print(f"📬 NEW REPLY FROM: {sender_email}")
                        print(f"📝 REPLY CONTENT: {content[:200]}...")
                        print(f"📊 ANALYTICS: {email_analytics['response_rate']}% response rate")
                        
                        # Don't auto-reply, just store the reply for manual response
                        print(f"📬 REPLY STORED FOR MANUAL RESPONSE: {sender_email}")
        
        mail.close()
        mail.logout()
        
        print(f"✅ REPLY CHECK COMPLETE: Found {new_replies} new replies")
        return jsonify({'success': True, 'replies_count': len(replies), 'new_replies': new_replies})
        
    except Exception as e:
        print(f"❌ REPLY CHECK FAILED: {str(e)}")
        return jsonify({'success': False, 'message': f'Error checking replies: {str(e)}'})


if __name__ == '__main__':
    print("🚀 STARTING SIMPLE WORKING EMAIL SYSTEM...")
    print(f"📧 Email: {EMAIL}")
    print(f"🤖 AI: {'Configured' if GEMINI_API_KEY else 'Not configured'}")
    print("🌐 Server starting on http://localhost:5008")
    
    app.run(debug=True, host='0.0.0.0', port=5008)
