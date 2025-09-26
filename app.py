from flask import Flask, render_template, request, jsonify, send_file
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime

app = Flask(__name__)

# Email Configuration
EMAIL = os.getenv('EMAIL', 'karmaterra427@gmail.com')
PASSWORD = os.getenv('PASSWORD', 'jidw kfwg hpsh diqi')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Simple data storage
contacts = []
sent_emails = []

@app.route('/')
def index():
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
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True)
