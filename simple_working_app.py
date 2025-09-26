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
        
        # Search for recent emails
        mail.search(None, 'ALL')
        
        # Get the last 10 emails
        _, message_numbers = mail.search(None, 'ALL')
        message_numbers = message_numbers[0].split()[-10:]  # Last 10 emails
        
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
                
                # Check if this is from someone we sent emails to
                sent_to_this_person = any(sent['recipient'].lower() == sender_email.lower() for sent in sent_emails)
                
                if sent_to_this_person:
                    # Check if we already have this reply
                    existing_reply = any(r['from_email'].lower() == sender_email.lower() for r in replies)
                    
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
                        
                        # Generate AI reply
                        ai_reply = generate_ai_reply(content, sender_email)
                        if ai_reply:
                            send_ai_reply(sender_email, subject, ai_reply, reply)
        
        mail.close()
        mail.logout()
        
        print(f"✅ REPLY CHECK COMPLETE: Found {new_replies} new replies")
        return jsonify({'success': True, 'replies_count': len(replies), 'new_replies': new_replies})
        
    except Exception as e:
        print(f"❌ REPLY CHECK FAILED: {str(e)}")
        return jsonify({'success': False, 'message': f'Error checking replies: {str(e)}'})

def generate_ai_reply(original_message, sender_email):
    """Generate AI reply using Gemini"""
    try:
        print(f"🤖 GENERATING AI REPLY for {sender_email}")
        
        prompt = f"""You are a professional email assistant. Someone replied to our email campaign with this message:

"{original_message}"

Please write a helpful, professional, and friendly response. Keep it concise and engaging. Do not mention that you are an AI."""

        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': GEMINI_API_KEY
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            ai_reply = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ AI REPLY GENERATED: {ai_reply[:100]}...")
            return ai_reply
        else:
            print(f"❌ AI API ERROR: {response.status_code}")
            return "Thank you for your email! We appreciate your response and will get back to you soon."
            
    except Exception as e:
        print(f"❌ AI GENERATION ERROR: {str(e)}")
        return "Thank you for your email! We appreciate your response and will get back to you soon."

def send_ai_reply(recipient, original_subject, ai_message, reply_obj):
    """Send AI-generated reply"""
    try:
        print(f"📤 SENDING AI REPLY TO: {recipient}")
        
        # Create reply email
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = recipient
        msg['Subject'] = f"Re: {original_subject.replace('Re: ', '')}"
        msg.set_content(ai_message)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Mark as AI replied
        reply_obj['ai_auto_replied'] = True
        reply_obj['ai_reply_text'] = ai_message
        
        print(f"✅ AI REPLY SENT TO: {recipient}")
        
    except Exception as e:
        print(f"❌ AI REPLY FAILED TO: {recipient} - {str(e)}")

if __name__ == '__main__':
    print("🚀 STARTING SIMPLE WORKING EMAIL SYSTEM...")
    print(f"📧 Email: {EMAIL}")
    print(f"🤖 AI: {'Configured' if GEMINI_API_KEY else 'Not configured'}")
    print("🌐 Server starting on http://localhost:5008")
    
    app.run(debug=True, host='0.0.0.0', port=5008)
