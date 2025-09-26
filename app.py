from flask import Flask, render_template, request, jsonify, send_file
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime
import requests
import json

app = Flask(__name__)

# Email Configuration
EMAIL = os.getenv('EMAIL', 'karmaterra427@gmail.com')
PASSWORD = os.getenv('PASSWORD', 'jidw kfwg hpsh diqi')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Simple data storage
contacts = []
sent_emails = []
replies = []

# 🤖 GEMINI AI FUNCTIONS
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
        
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            result = response.json()
            ai_reply = result['candidates'][0]['content']['parts'][0]['text']
            return ai_reply.strip()
        else:
            print(f"❌ GEMINI API ERROR: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ AI REPLY ERROR: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('unified_dashboard.html')

@app.route('/test')
def test_page():
    return send_file('test.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'message': 'AI Email System is running!'})

@app.route('/api/test')
def test():
    return jsonify({'message': 'Test endpoint working!', 'timestamp': '2024-01-01'})

# Basic email functionality
@app.route('/api/contacts')
def get_contacts():
    return jsonify(contacts)

@app.route('/api/add-contact', methods=['POST'])
def add_contact():
    global contacts
    
    email_addr = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if not email_addr or not first_name or not last_name:
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    # Check for duplicates
    for contact in contacts:
        if contact['email'].lower() == email_addr.lower():
            return jsonify({'success': False, 'message': 'Email already exists'})
    
    # Add new contact
    new_contact = {
        'id': len(contacts) + 1,
        'email': email_addr,
        'first_name': first_name,
        'last_name': last_name,
        'status': 'Not Sent',
        'added_date': datetime.now().isoformat()
    }
    
    contacts.append(new_contact)
    return jsonify({'success': True, 'message': 'Contact added successfully'})

@app.route('/api/send-email', methods=['POST'])
def send_email():
    """Send a single test email"""
    global sent_emails
    
    recipient = request.form.get('email')
    subject = request.form.get('subject', 'Test Email')
    message = request.form.get('message', 'This is a test email from AI Email System')
    
    if not recipient:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    try:
        # Create email
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.set_content(message)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Track sent email
        sent_emails.append({
            'recipient': recipient,
            'subject': subject,
            'sent_date': datetime.now().isoformat(),
            'status': 'sent'
        })
        
        return jsonify({'success': True, 'message': f'Email sent to {recipient}'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error sending email: {str(e)}'})

@app.route('/api/stats')
def get_stats():
    """Get basic statistics"""
    return jsonify({
        'total_contacts': len(contacts),
        'total_emails_sent': len(sent_emails),
        'total_replies': len(replies),
        'timestamp': datetime.now().isoformat()
    })

# 🤖 AI REPLY ENDPOINTS
@app.route('/api/replies')
def get_replies():
    """Get all replies"""
    return jsonify(replies)

@app.route('/api/generate-ai-reply', methods=['POST'])
def generate_reply():
    """Generate AI reply for a message"""
    data = request.get_json()
    message = data.get('message', '')
    sender_name = data.get('sender_name', '')
    
    if not message:
        return jsonify({'success': False, 'message': 'Message is required'})
    
    ai_reply = generate_ai_reply(message, sender_name)
    
    if ai_reply:
        return jsonify({
            'success': True, 
            'ai_reply': ai_reply,
            'message': 'AI reply generated successfully'
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Failed to generate AI reply'
        })

@app.route('/api/send-ai-reply', methods=['POST'])
def send_ai_reply():
    """Send AI-generated reply"""
    data = request.get_json()
    recipient = data.get('email')
    original_message = data.get('original_message', '')
    sender_name = data.get('sender_name', '')
    
    if not recipient:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    # Generate AI reply
    ai_reply = generate_ai_reply(original_message, sender_name)
    
    if not ai_reply:
        return jsonify({'success': False, 'message': 'Failed to generate AI reply'})
    
    try:
        # Create email
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = recipient
        msg['Subject'] = 'Re: Your Message'
        msg.set_content(ai_reply)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Track the reply
        replies.append({
            'recipient': recipient,
            'ai_reply': ai_reply,
            'original_message': original_message,
            'sent_date': datetime.now().isoformat(),
            'status': 'sent'
        })
        
        return jsonify({
            'success': True, 
            'message': f'AI reply sent to {recipient}',
            'ai_reply': ai_reply
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error sending AI reply: {str(e)}'
        })

if __name__ == '__main__':
    app.run(debug=True)
