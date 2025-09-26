#!/usr/bin/env python3

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

# SIMPLE DATA STORAGE
contacts = []
sent_emails = []
replies = []
monitoring_active = False

@app.route('/')
def index():
    return render_template('unified_dashboard.html')

@app.route('/get-contacts')
def get_contacts():
    """Get all contacts"""
    print(f"📋 GET CONTACTS: {len(contacts)} contacts")
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
                
                # Track sent email
                sent_emails.append({
                    'recipient': contact['email'],
                    'subject': subject,
                    'sent_date': datetime.now().isoformat()
                })
                
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
        
        print(f"✅ MANUAL REPLY SENT TO: {original_reply['from_email']}")
        
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

@app.route('/api/analytics/dashboard')
def get_analytics():
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
                        
                        print(f"📬 NEW REPLY FROM: {sender_email}")
                        print(f"📝 REPLY CONTENT: {content[:200]}...")
                        
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
