"""
Vercel Serverless Function Entry Point
AI Email Campaign Manager - Production Deployment
"""

import os
import sys
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
monitoring_active = False

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

@app.route('/api/contacts')
def get_contacts_api():
    """Get all contacts - API endpoint"""
    return jsonify(contacts)

@app.route('/add-contact', methods=['POST'])
def add_contact():
    """Add a single contact"""
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
        'monitoring': monitoring_active,
        'status': 'active' if monitoring_active else 'inactive'
    })

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    global monitoring_active
    monitoring_active = True
    return jsonify({'success': True, 'message': 'Email monitoring started'})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    global monitoring_active
    monitoring_active = False
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
    """Upload bulk contacts from file"""
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
    
    return jsonify({'success': True, 'message': 'Campaign reset successfully'})

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda *args: None)
