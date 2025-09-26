#!/usr/bin/env python3
"""
AI Email Automation System - Vercel Optimized
Enhanced with comprehensive tracking and Gemini AI integration
"""

from flask import Flask, render_template, request, jsonify
import smtplib
from email.message import EmailMessage
import imaplib
import email
import re
from datetime import datetime
import time
import requests
import json
import os

# Initialize Flask app
app = Flask(__name__)

# Email Configuration
EMAIL = os.getenv('EMAIL', 'karmaterra427@gmail.com')
PASSWORD = os.getenv('PASSWORD', 'jidw kfwg hpsh diqi')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8')
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Global data storage (in-memory for serverless)
contacts = []
sent_emails = []
replies = []

# Email analytics
email_analytics = {
    'total_sent': 0,
    'total_replies': 0,
    'response_rate': 0.0,
    'avg_response_time_hours': 0,
    'campaigns_today': 0,
    'ai_auto_replies': 0,
    'manual_replies': 0,
    'daily_stats': {}
}

def calculate_analytics():
    """Calculate comprehensive email analytics"""
    global email_analytics, sent_emails, replies
    
    email_analytics['total_sent'] = len(sent_emails)
    email_analytics['total_replies'] = len(replies)
    
    if email_analytics['total_sent'] > 0:
        email_analytics['response_rate'] = round((email_analytics['total_replies'] / email_analytics['total_sent']) * 100, 2)
    else:
        email_analytics['response_rate'] = 0.0
    
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
    email_analytics['total_sent'] += 1

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
        'avg_response_time': f"{analytics['avg_response_time_hours']:.1f} hours",
        'campaigns_today': analytics['campaigns_today'],
        'ai_auto_replies': analytics['ai_auto_replies'],
        'manual_replies': analytics['manual_replies'],
        'success_rate': f"{(analytics['ai_auto_replies'] / max(analytics['total_replies'], 1) * 100):.1f}%"
    }
    
    return jsonify(stats)

@app.route('/get-contacts')
def get_contacts():
    """Get all contacts"""
    return jsonify(contacts)

@app.route('/add-contact', methods=['POST'])
def add_contact():
    """Add a single contact"""
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

@app.route('/start-manual-campaign', methods=['POST'])
def start_campaign():
    """Start email campaign - Serverless optimized"""
    global contacts, sent_emails
    
    if not contacts:
        return jsonify({'success': False, 'message': 'No contacts added yet'})
    
    subject = request.form.get('subject', 'Your Email Campaign')
    message = request.form.get('message', 'Hello! This is our email campaign.')
    
    sent_count = 0
    failed_count = 0
    
    # Limit to first 5 contacts for serverless environment
    contacts_to_send = [c for c in contacts if c['status'] != 'Sent'][:5]
    
    for contact in contacts_to_send:
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
            
            # Send email with timeout
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL, PASSWORD)
                server.send_message(msg)
            
            # Mark as sent
            contact['status'] = 'Sent'
            contact['sent_date'] = datetime.now().isoformat()
            
            # Track email
            track_email_sent(contact['email'], subject, "Campaign")
            sent_count += 1
            
        except Exception as e:
            failed_count += 1
            print(f"Email send failed: {str(e)}")
    
    return jsonify({
        'success': True, 
        'message': f'Campaign completed! Sent: {sent_count}, Failed: {failed_count}'
    })

@app.route('/api/replies')
def get_replies():
    """Get all replies"""
    return jsonify(replies)

@app.route('/api/send-ai-reply', methods=['POST'])
def send_ai_reply():
    """Send AI-generated reply to a specific email"""
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

# Health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# For Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)
