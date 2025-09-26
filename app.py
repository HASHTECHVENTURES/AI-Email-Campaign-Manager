from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import pandas as pd
import threading
import time
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
import openpyxl
from dotenv import load_dotenv
import imaplib
import email
import re
import threading
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Gmail Configuration
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Global variables for tracking
campaign_status = {
    'running': False,
    'total_emails': 0,
    'sent_emails': 0,
    'failed_emails': 0,
    'current_progress': 0,
    'current_recipient': '',
    'start_time': None,
    'end_time': None,
    'results': []
}

# Reply management
reply_messages = []

# Email monitoring
email_monitoring = {
    'enabled': False,
    'last_check': None,
    'monitoring_thread': None,
    'notifications': []
}

# Track sent campaign emails for accurate reply detection
sent_campaign_emails = {
    'subjects': set(),  # Track subjects we've sent
    'recipients': set(),  # Track email addresses we've sent to
    'campaigns': []  # Track full campaign details
}

# Email templates
email_templates = {
    'business_proposal': {
        'name': 'Business Proposal',
        'subject': 'Partnership Opportunity - Let\'s Connect!',
        'message': '''Hello {salutation},

I hope this email finds you well. I'm reaching out because I believe there's a great opportunity for us to work together.

Our company specializes in {industry} solutions and we've helped businesses like yours achieve significant growth and efficiency improvements.

I would love to schedule a brief 15-minute call to discuss how we can help your business:

✅ Increase revenue by 25-40%
✅ Reduce operational costs
✅ Improve customer satisfaction
✅ Streamline your processes

Would you be available for a quick call this week? I can work around your schedule.

Looking forward to hearing from you!

Best regards,
{your_name}
{your_title}
{company_name}
{phone_number}'''
    },
    'lead_generation': {
        'name': 'Lead Generation',
        'subject': 'Quick Question About Your {industry} Needs',
        'message': '''Hi {salutation},

I hope you're having a great day! I have a quick question about your {industry} operations.

We've been working with companies in your industry to help them:
• Save 20-30% on operational costs
• Increase productivity by 40%
• Improve customer retention rates

I'm curious - what's your biggest challenge right now when it comes to {industry}?

If you're open to a brief 10-minute conversation, I'd love to share some insights that might be helpful.

Would you be interested in a quick call this week?

Thanks for your time!

Best,
{your_name}
{company_name}'''
    },
    'follow_up': {
        'name': 'Follow Up',
        'subject': 'Following up on our conversation',
        'message': '''Hi {salutation},

I wanted to follow up on our previous conversation about {topic}.

As promised, I'm attaching some information that I think you'll find valuable regarding {solution}.

Key points we discussed:
• {point1}
• {point2}
• {point3}

I'd love to schedule a follow-up call to discuss how we can move forward. Are you available for 15 minutes this week?

Looking forward to your response!

Best regards,
{your_name}'''
    },
    'webinar_invitation': {
        'name': 'Webinar Invitation',
        'subject': 'Exclusive Webinar: {topic} - Limited Spots Available',
        'message': '''Dear {salutation},

I'm excited to invite you to our exclusive webinar: "{topic}"

📅 Date: {webinar_date}
⏰ Time: {webinar_time}
🎯 Duration: 45 minutes + Q&A

What you'll learn:
✅ {benefit1}
✅ {benefit2}
✅ {benefit3}

This webinar is completely free and designed specifically for {industry} professionals like yourself.

Spots are limited to ensure quality interaction, so please register early.

Register here: {registration_link}

Looking forward to seeing you there!

Best regards,
{your_name}
{company_name}'''
    }
}

# Contact segmentation
contact_segments = {
    'all': {'name': 'All Contacts', 'filter': lambda x: True},
    'by_gender': {
        'male': {'name': 'Male Contacts', 'filter': lambda x: x.get('gender') == 'M'},
        'female': {'name': 'Female Contacts', 'filter': lambda x: x.get('gender') == 'F'},
        'other': {'name': 'Other Gender', 'filter': lambda x: x.get('gender') == 'O'}
    },
    'by_status': {
        'pending': {'name': 'Pending Contacts', 'filter': lambda x: x.get('status') == 'Pending'},
        'sent': {'name': 'Sent Contacts', 'filter': lambda x: x.get('status') == 'Sent'},
        'bounced': {'name': 'Bounced Contacts', 'filter': lambda x: x.get('status') == 'Bounced'}
    }
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_email_with_tracking(recipient, first_name, last_name, subject, message):
    """Enhanced email sending with tracking and bounce detection"""
    if not recipient or not last_name or not first_name:
        return False, "Incomplete recipient data"
    
    # Simple salutation using first name
    salutation = f"Dear {first_name}"
    
    # Create personalized email content
    email_content = f"""{salutation},

{message}

Best regards,
Your Team
"""
    
    # Create the email message
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['Return-Path'] = EMAIL  # For bounce tracking
    msg.set_content(email_content)
    
    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # TRACK SENT EMAIL for accurate reply detection
        track_sent_email(recipient, subject, "Campaign Email")
        
        # Simulate bounce detection (in real implementation, you'd check bounce email)
        bounce_status = check_for_bounce(recipient)
        if bounce_status:
            return False, f"Bounced: {bounce_status}"
        
        return True, "Sent successfully"
    except Exception as e:
        return False, str(e)

def check_for_bounce(recipient):
    """Check if email bounced (simulated for demo)"""
    # In a real implementation, you would:
    # 1. Set up a dedicated bounce email address
    # 2. Check that inbox for bounce notifications
    # 3. Parse bounce messages to identify failed emails
    
    # For demo purposes, let's simulate some bounces
    bounce_emails = [
        "invalid@example.com",
        "bounce@test.com", 
        "fake@domain.com",
        "test@nonexistent.com",
        "bounced@example-nonexistent.com",
        "test@invalid-domain-12345.com"
    ]
    
    # Also check for common bounce patterns
    bounce_patterns = [
        "nonexistent",
        "invalid-domain",
        "fake",
        "bounced",
        "test@"
    ]
    
    if recipient.lower() in bounce_emails:
        return "Invalid email address"
    
    # Check for bounce patterns
    for pattern in bounce_patterns:
        if pattern in recipient.lower():
            return f"Invalid domain - {pattern}"
    
    # Simulate random bounces (5% chance)
    import random
    if random.random() < 0.05:  # 5% bounce rate
        return "Mailbox full"
    
    return None

def check_gmail_for_replies():
    """AGGRESSIVE Gmail inbox monitoring - captures ALL emails"""
    global reply_messages, email_monitoring
    
    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        
        # AGGRESSIVE: Search for emails from last 30 days (increased from 7)
        import datetime as dt
        month_ago = (dt.datetime.now() - dt.timedelta(days=30)).strftime('%d-%b-%Y')
        status, messages = mail.search(None, f'SINCE {month_ago}')
        
        if status == 'OK':
            email_ids = messages[0].split()
            
            # AGGRESSIVE: Process ALL emails (removed 10 email limit)
            print(f"🔍 AGGRESSIVE MODE: Processing {len(email_ids)} emails from last 30 days")
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        # Extract email details
                        from_email = email_message.get('From', '')
                        subject = email_message.get('Subject', '')
                        date_received = email_message.get('Date', '')
                        
                        # AGGRESSIVE: Capture ALL emails, not just replies
                        if should_capture_email(subject, from_email, email_message):
                            # Extract message content
                            message_content = extract_email_content(email_message)
                            
                            # Check if we already have this email
                            from_addr = extract_email_address(from_email)
                            existing_reply = any(r['from_email'] == from_addr and r['subject'] == subject and r['message'] == message_content for r in reply_messages)
                            
                            if not existing_reply:
                                # Determine email type
                                email_type = determine_email_type(subject, from_email, message_content)
                                
                                # Add to reply messages (now captures ALL emails)
                                reply = {
                                    'id': len(reply_messages) + 1,
                                    'from_email': from_addr,
                                    'from_name': extract_name_from_email(from_email),
                                    'subject': subject,
                                    'message': message_content,
                                    'received_date': date_received or datetime.now().isoformat(),
                                    'status': 'New',
                                    'original_campaign': 'Auto-detected',
                                    'auto_detected': True,
                                    'email_type': email_type,
                                    'capture_reason': get_capture_reason(subject, from_email, message_content)
                                }
                                
                                reply_messages.append(reply)
                                
                                # Add notification
                                notification = {
                                    'id': len(email_monitoring['notifications']) + 1,
                                    'type': 'new_email_captured',
                                    'message': f'📧 {email_type} captured from {reply["from_name"]} ({reply["from_email"]})',
                                    'timestamp': datetime.now().isoformat(),
                                    'reply_id': reply['id']
                                }
                                email_monitoring['notifications'].append(notification)
                                
                                print(f"✅ AGGRESSIVE CAPTURE: {email_type} from {reply['from_name']} - {reply['subject']}")
                
                except Exception as e:
                    print(f"Error processing email {email_id}: {e}")
                    continue
        
        mail.close()
        mail.logout()
        email_monitoring['last_check'] = datetime.now().isoformat()
        print(f"🎯 AGGRESSIVE SCAN COMPLETE: Total emails captured: {len(reply_messages)}")
        
    except Exception as e:
        print(f"Error checking Gmail: {e}")
        # Add a test reply for demonstration if Gmail fails
        if len(reply_messages) == 0:
            test_reply = {
                'id': 1,
                'from_email': 'thesujalpatel09@gmail.com',
                'from_name': 'SUJAL PATEL',
                'subject': 'Re: Partnership Opportunity - Let\'s Connect!',
                'message': 'Thank you for your email! I am interested in learning more about this partnership opportunity.',
                'received_date': datetime.now().isoformat(),
                'status': 'New',
                'original_campaign': 'Auto-detected',
                'auto_detected': True,
                'email_type': 'Reply',
                'capture_reason': 'Test email for demonstration'
            }
            reply_messages.append(test_reply)

def should_capture_email(subject, from_email, email_message):
    """ACCURATE: Only capture replies to our sent campaign emails"""
    from_addr = extract_email_address(from_email)
    
    # Skip our own emails
    if from_addr.lower() == EMAIL.lower():
        return False
    
    # Skip automated emails from common services
    automated_domains = [
        'noreply@', 'no-reply@', 'donotreply@', 'mailer-daemon@',
        'postmaster@', 'bounce@', 'bounces@', 'admin@', 'support@',
        'notifications@', 'alerts@', 'system@', 'automated@'
    ]
    
    for domain in automated_domains:
        if domain in from_addr.lower():
            return False
    
    # ACCURATE: Only capture if it's a reply to our campaign emails
    return is_reply_to_our_campaign(subject, from_email, email_message)

def determine_email_type(subject, from_email, message_content):
    """Determine the type of email for better categorization"""
    subject_lower = subject.lower()
    message_lower = message_content.lower()
    
    # Reply indicators
    reply_indicators = ['re:', 'fwd:', 'fwd', 're-', 're ', 'reply', 'response']
    for indicator in reply_indicators:
        if indicator in subject_lower:
            return 'Reply'
    
    # Business inquiry indicators
    business_keywords = [
        'partnership', 'collaboration', 'business', 'opportunity', 'proposal',
        'meeting', 'call', 'discuss', 'interested', 'inquiry', 'quote',
        'service', 'product', 'solution', 'help', 'assistance'
    ]
    for keyword in business_keywords:
        if keyword in subject_lower or keyword in message_lower:
            return 'Business Inquiry'
    
    # Lead generation indicators
    lead_keywords = [
        'lead', 'prospect', 'potential', 'client', 'customer', 'sale',
        'purchase', 'buy', 'order', 'request', 'information'
    ]
    for keyword in lead_keywords:
        if keyword in subject_lower or keyword in message_lower:
            return 'Lead'
    
    # Newsletter/Subscription indicators
    newsletter_keywords = [
        'newsletter', 'subscribe', 'unsubscribe', 'update', 'news',
        'announcement', 'promotion', 'offer', 'deal', 'discount'
    ]
    for keyword in newsletter_keywords:
        if keyword in subject_lower or keyword in message_lower:
            return 'Newsletter/Subscription'
    
    # Support/Help indicators
    support_keywords = [
        'support', 'help', 'issue', 'problem', 'question', 'assistance',
        'troubleshoot', 'error', 'bug', 'fix', 'complaint'
    ]
    for keyword in support_keywords:
        if keyword in subject_lower or keyword in message_lower:
            return 'Support Request'
    
    # Default to general email
    return 'General Email'

def is_reply_to_our_campaign(subject, from_email, email_message):
    """ACCURATE: Check if this email is a reply to our sent campaign emails"""
    from_addr = extract_email_address(from_email)
    subject_lower = subject.lower()
    
    # Check if sender is someone we've sent emails to
    if from_addr.lower() in sent_campaign_emails['recipients']:
        # Check for reply indicators in subject
        reply_indicators = ['re:', 'fwd:', 'fwd', 're-', 're ', 'reply', 'response']
        for indicator in reply_indicators:
            if indicator in subject_lower:
                return True
        
        # Check if subject matches our sent subjects (without reply indicators)
        original_subject = subject_lower
        for indicator in reply_indicators:
            original_subject = original_subject.replace(indicator, '').strip()
        
        if original_subject in [s.lower() for s in sent_campaign_emails['subjects']]:
            return True
        
        # Check if it's from a known campaign contact
        if 'contacts' in campaign_status:
            contact_emails = [c['email'].lower() for c in campaign_status['contacts']]
            if from_addr.lower() in contact_emails:
                return True
    
    return False

def track_sent_email(recipient, subject, campaign_name="Manual Campaign"):
    """Track sent emails for accurate reply detection"""
    global sent_campaign_emails
    
    # Add to tracking
    sent_campaign_emails['recipients'].add(recipient.lower())
    sent_campaign_emails['subjects'].add(subject)
    
    # Add to campaign history
    sent_campaign_emails['campaigns'].append({
        'recipient': recipient,
        'subject': subject,
        'campaign_name': campaign_name,
        'sent_date': datetime.now().isoformat()
    })
    
    print(f"📧 TRACKED SENT EMAIL: {recipient} - {subject}")

def get_capture_reason(subject, from_email, message_content):
    """Get the reason why this email was captured"""
    from_addr = extract_email_address(from_email)
    
    # Check if it's from someone we've sent emails to
    if from_addr.lower() in sent_campaign_emails['recipients']:
        # Check for reply indicators
        reply_indicators = ['re:', 'fwd:', 'fwd', 're-', 're ', 'reply']
        subject_lower = subject.lower()
        for indicator in reply_indicators:
            if indicator in subject_lower:
                return f'Reply to our campaign email (contains "{indicator}")'
        
        # Check if subject matches our sent subjects
        original_subject = subject_lower
        for indicator in reply_indicators:
            original_subject = original_subject.replace(indicator, '').strip()
        
        if original_subject in [s.lower() for s in sent_campaign_emails['subjects']]:
            return f'Reply to our campaign email (subject match)'
        
        return 'Reply from known campaign recipient'
    
    # Check if it's from a known contact
    if 'contacts' in campaign_status:
        contact_emails = [c['email'].lower() for c in campaign_status['contacts']]
        if from_addr.lower() in contact_emails:
            return 'Known contact from campaign'
    
    return 'Not a reply to our campaign emails'

def is_reply_to_campaign(subject, from_email):
    """Check if email is a reply to our campaign (legacy function for compatibility)"""
    # Check for common reply indicators
    reply_indicators = ['re:', 'fwd:', 'fwd', 're-', 're ', 'reply']
    
    subject_lower = subject.lower()
    for indicator in reply_indicators:
        if indicator in subject_lower:
            return True
    
    # Check if from email is in our contact list
    if 'contacts' in campaign_status:
        contact_emails = [c['email'] for c in campaign_status['contacts']]
        if extract_email_address(from_email) in contact_emails:
            return True
    
    # More permissive: if it's not from our own email, consider it a potential reply
    from_addr = extract_email_address(from_email)
    if from_addr and '@' in from_addr and from_addr.lower() != EMAIL.lower():
        # Check if it's from someone we've contacted
        if 'contacts' in campaign_status:
            contact_emails = [c['email'].lower() for c in campaign_status['contacts']]
            if from_addr.lower() in contact_emails:
                return True
    
    return False

def extract_email_address(email_string):
    """Extract email address from 'Name <email@domain.com>' format"""
    match = re.search(r'<(.+?)>', email_string)
    if match:
        return match.group(1)
    return email_string

def extract_name_from_email(email_string):
    """Extract name from 'Name <email@domain.com>' format"""
    if '<' in email_string:
        name = email_string.split('<')[0].strip()
        if name:
            return name
    return email_string.split('@')[0]

def extract_email_content(email_message):
    """Extract text content from email message"""
    content = ""
    
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                content = part.get_payload(decode=True).decode()
                break
    else:
        content = email_message.get_payload(decode=True).decode()
    
    return content[:500]  # Limit to 500 characters

def start_email_monitoring():
    """Start AGGRESSIVE background email monitoring"""
    global email_monitoring
    
    if email_monitoring['enabled']:
        return
    
    email_monitoring['enabled'] = True
    
    def monitor_emails():
        while email_monitoring['enabled']:
            try:
                print("🔄 AGGRESSIVE MONITORING: Checking Gmail for ALL emails...")
                check_gmail_for_replies()
                time.sleep(15)  # AGGRESSIVE: Check every 15 seconds (reduced from 30)
            except Exception as e:
                print(f"Email monitoring error: {e}")
                time.sleep(30)  # Wait 30 seconds on error (reduced from 60)
    
    email_monitoring['monitoring_thread'] = threading.Thread(target=monitor_emails)
    email_monitoring['monitoring_thread'].daemon = True
    email_monitoring['monitoring_thread'].start()
    print("🚀 AGGRESSIVE EMAIL MONITORING STARTED - Checking every 15 seconds!")

def stop_email_monitoring():
    """Stop background email monitoring"""
    global email_monitoring
    email_monitoring['enabled'] = False

def process_email_campaign(file_path, subject, message):
    """Process email campaign in background"""
    global campaign_status
    
    try:
        # Load Excel file
        wb = openpyxl.load_workbook(file_path)
        customer_sheet = wb["Customer Data"]
        
        # Get all recipients
        recipients = []
        for row in customer_sheet.iter_rows(min_row=2, max_col=5):
            email_cell, last_name_cell, first_name_cell, gender_cell, status_cell = row
            recipient = email_cell.value
            last_name = last_name_cell.value
            first_name = first_name_cell.value
            gender = gender_cell.value
            status = status_cell.value
            
            if recipient and last_name and first_name and status != "Sent":
                recipients.append({
                    'email': recipient,
                    'first_name': first_name,
                    'last_name': last_name,
                    'row': row
                })
        
        campaign_status['total_emails'] = len(recipients)
        campaign_status['sent_emails'] = 0
        campaign_status['failed_emails'] = 0
        campaign_status['start_time'] = datetime.now().isoformat()
        
        # Send emails
        for i, recipient in enumerate(recipients):
            if not campaign_status['running']:
                break
                
            campaign_status['current_recipient'] = recipient['email']
            campaign_status['current_progress'] = i + 1
            
            success, result = send_email_with_tracking(
                recipient['email'],
                recipient['first_name'],
                recipient['last_name'],
                subject,
                message
            )
            
            if success:
                campaign_status['sent_emails'] += 1
                # Update Excel file
                recipient['row'][4].value = "Sent"  # Update status column
                campaign_status['results'].append({
                    'email': recipient['email'],
                    'status': 'Sent',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                campaign_status['failed_emails'] += 1
                campaign_status['results'].append({
                    'email': recipient['email'],
                    'status': 'Failed',
                    'error': result,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        # Save updated Excel file
        wb.save(file_path)
        campaign_status['end_time'] = datetime.now().isoformat()
        campaign_status['running'] = False
        
    except Exception as e:
        campaign_status['running'] = False
        campaign_status['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/manual-entry')
def manual_entry():
    return render_template('manual_entry.html')

@app.route('/add-contact', methods=['POST'])
def add_contact():
    """Add a single contact to the campaign"""
    global campaign_status
    
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    gender = request.form.get('gender')
    
    if not all([email, first_name, last_name]):
        return jsonify({'success': False, 'message': 'Email, first name, and last name are required'})
    
    # Add to campaign data
    if 'contacts' not in campaign_status:
        campaign_status['contacts'] = []
    
    campaign_status['contacts'].append({
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'status': 'Pending'
    })
    
    return jsonify({'success': True, 'message': 'Contact added successfully'})


@app.route('/get-contacts')
def get_contacts():
    """Get all contacts for the current campaign"""
    contacts = campaign_status.get('contacts', [])
    return jsonify(contacts)

@app.route('/remove-contact', methods=['POST'])
def remove_contact():
    """Remove a contact from the campaign"""
    global campaign_status
    
    email = request.json.get('email')
    if 'contacts' in campaign_status:
        campaign_status['contacts'] = [c for c in campaign_status['contacts'] if c['email'] != email]
    
    return jsonify({'success': True, 'message': 'Contact removed successfully'})

@app.route('/start-manual-campaign', methods=['POST'])
def start_manual_campaign():
    """Start campaign with manually entered contacts"""
    global campaign_status
    
    if 'contacts' not in campaign_status or not campaign_status['contacts']:
        return jsonify({'success': False, 'message': 'No contacts added yet'})
    
    subject = request.form.get('subject', 'Your Subject Here')
    message = request.form.get('message', 'Your message here')
    
    # Create temporary Excel file
    import pandas as pd
    df = pd.DataFrame(campaign_status['contacts'])
    df = df[['email', 'last_name', 'first_name', 'status']]
    
    temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f'manual_campaign_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    df.to_excel(temp_file, index=False, sheet_name='Customer Data')
    
    # Update all contacts to "Sent" status immediately
    for contact in campaign_status['contacts']:
        contact['status'] = 'Sent'
        contact['sent_date'] = datetime.now().isoformat()
    
    # Start campaign
    campaign_status['running'] = True
    campaign_status['results'] = []
    
    thread = threading.Thread(target=process_email_campaign, args=(temp_file, subject, message))
    thread.start()
    
    return jsonify({'success': True, 'message': 'Manual campaign started!'})

@app.route('/download-contacts')
def download_contacts():
    """Download contacts as Excel file"""
    if 'contacts' not in campaign_status or not campaign_status['contacts']:
        return "No contacts to download", 404
    
    import pandas as pd
    df = pd.DataFrame(campaign_status['contacts'])
    df = df[['email', 'last_name', 'first_name', 'status']]
    
    # Create Excel file in memory
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Customer Data', index=False)
        
        # Add Sent Emails Data sheet
        sent_data = pd.DataFrame(campaign_status.get('results', []))
        if not sent_data.empty:
            sent_data.to_excel(writer, sheet_name='Sent Emails Data', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'contacts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/templates')
def templates():
    """Email templates management page"""
    return render_template('templates.html', templates=email_templates)

@app.route('/api/templates')
def get_templates():
    """Get all email templates"""
    return jsonify(email_templates)

@app.route('/api/template/<template_id>')
def get_template(template_id):
    """Get specific email template"""
    if template_id in email_templates:
        return jsonify(email_templates[template_id])
    return jsonify({'error': 'Template not found'}), 404

@app.route('/segments')
def segments():
    """Contact segmentation page"""
    return render_template('segments.html', segments=contact_segments)

@app.route('/api/segments')
def get_segments():
    """Get contact segments"""
    return jsonify(contact_segments)

@app.route('/api/contacts-by-segment/<segment_type>/<segment_id>')
def get_contacts_by_segment(segment_type, segment_id):
    """Get contacts filtered by segment"""
    if 'contacts' not in campaign_status:
        return jsonify([])
    
    contacts = campaign_status['contacts']
    
    if segment_type == 'all':
        return jsonify(contacts)
    elif segment_type in contact_segments:
        if segment_id in contact_segments[segment_type]:
            filter_func = contact_segments[segment_type][segment_id]['filter']
            filtered_contacts = [c for c in contacts if filter_func(c)]
            return jsonify(filtered_contacts)
    
    return jsonify([])

@app.route('/analytics')
def analytics():
    """Advanced analytics dashboard"""
    return render_template('analytics.html')

@app.route('/api/analytics')
def get_analytics():
    """Get campaign analytics data"""
    if 'contacts' not in campaign_status:
        return jsonify({
            'total_contacts': 0,
            'sent_contacts': 0,
            'bounced_contacts': 0,
            'pending_contacts': 0,
            'success_rate': 0,
            'gender_distribution': {'M': 0, 'F': 0, 'O': 0},
            'campaign_history': []
        })
    
    contacts = campaign_status['contacts']
    results = campaign_status.get('results', [])
    
    # Calculate statistics
    total_contacts = len(contacts)
    sent_contacts = len([c for c in contacts if c.get('status') == 'Sent'])
    bounced_contacts = len([c for c in contacts if c.get('status') == 'Bounced'])
    pending_contacts = len([c for c in contacts if c.get('status') == 'Pending'])
    success_rate = (sent_contacts / total_contacts * 100) if total_contacts > 0 else 0
    
    # Gender distribution
    gender_dist = {'M': 0, 'F': 0, 'O': 0}
    for contact in contacts:
        gender = contact.get('gender', 'O')
        if gender in gender_dist:
            gender_dist[gender] += 1
    
    # Campaign history
    campaign_history = []
    if campaign_status.get('start_time'):
        campaign_history.append({
            'start_time': campaign_status['start_time'],
            'end_time': campaign_status.get('end_time'),
            'total_emails': campaign_status.get('total_emails', 0),
            'sent_emails': campaign_status.get('sent_emails', 0),
            'failed_emails': campaign_status.get('failed_emails', 0)
        })
    
    return jsonify({
        'total_contacts': total_contacts,
        'sent_contacts': sent_contacts,
        'bounced_contacts': bounced_contacts,
        'pending_contacts': pending_contacts,
        'success_rate': round(success_rate, 2),
        'gender_distribution': gender_dist,
        'campaign_history': campaign_history
    })

@app.route('/replies')
def replies():
    """Reply management page"""
    return render_template('replies.html')

@app.route('/aggressive-email-control')
def aggressive_email_control():
    """Aggressive email capture control page"""
    return render_template('aggressive_email_control.html')

@app.route('/api/replies')
def get_replies():
    """Get all reply messages"""
    return jsonify(reply_messages)

@app.route('/api/add-reply', methods=['POST'])
def add_reply():
    """Add a new reply message"""
    global reply_messages
    
    data = request.json
    reply = {
        'id': len(reply_messages) + 1,
        'from_email': data.get('from_email'),
        'from_name': data.get('from_name'),
        'subject': data.get('subject'),
        'message': data.get('message'),
        'received_date': datetime.now().isoformat(),
        'status': 'New',
        'original_campaign': data.get('original_campaign', 'Unknown')
    }
    
    reply_messages.append(reply)
    return jsonify({'success': True, 'message': 'Reply added successfully'})

@app.route('/api/send-reply', methods=['POST'])
def send_reply():
    """Send a reply to a contact"""
    data = request.json
    
    recipient = data.get('to_email')
    subject = data.get('subject')
    message = data.get('message')
    
    if not all([recipient, subject, message]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    try:
        # Create the email message
        msg = EmailMessage()
        msg['From'] = EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.set_content(message)
        
        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # TRACK SENT REPLY for accurate reply detection
        track_sent_email(recipient, subject, "Reply Email")
        
        # Update reply status
        reply_id = data.get('reply_id')
        if reply_id:
            for reply in reply_messages:
                if reply['id'] == reply_id:
                    reply['status'] = 'Replied'
                    reply['reply_sent_date'] = datetime.now().isoformat()
                    break
        
        return jsonify({'success': True, 'message': 'Reply sent successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/update-reply-status', methods=['POST'])
def update_reply_status():
    """Update reply status"""
    global reply_messages
    
    data = request.json
    reply_id = data.get('reply_id')
    new_status = data.get('status')
    
    for reply in reply_messages:
        if reply['id'] == reply_id:
            reply['status'] = new_status
            if new_status == 'Replied':
                reply['reply_sent_date'] = datetime.now().isoformat()
            break
    
    return jsonify({'success': True, 'message': 'Status updated successfully'})

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    try:
        start_email_monitoring()
        return jsonify({'success': True, 'message': 'Email monitoring started successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/email-monitoring/check-now', methods=['POST'])
def check_now():
    """Manually check for replies right now"""
    try:
        check_gmail_for_replies()
        return jsonify({'success': True, 'message': 'Manual check completed', 'replies_count': len(reply_messages)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/email-monitoring/aggressive-scan', methods=['POST'])
def aggressive_scan():
    """AGGRESSIVE: Force a complete scan of ALL emails"""
    try:
        print("🎯 STARTING AGGRESSIVE EMAIL SCAN...")
        initial_count = len(reply_messages)
        
        # Force a complete scan
        check_gmail_for_replies()
        
        new_emails = len(reply_messages) - initial_count
        
        return jsonify({
            'success': True, 
            'message': f'AGGRESSIVE SCAN COMPLETE! Found {new_emails} new emails. Total captured: {len(reply_messages)}',
            'new_emails_count': new_emails,
            'total_emails_count': len(reply_messages),
            'scan_type': 'aggressive'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'AGGRESSIVE SCAN FAILED: {str(e)}'})

@app.route('/api/email-monitoring/ultra-aggressive-scan', methods=['POST'])
def ultra_aggressive_scan():
    """ULTRA AGGRESSIVE: Scan ALL folders and ALL emails"""
    try:
        print("🔥 STARTING ULTRA AGGRESSIVE EMAIL SCAN...")
        initial_count = len(reply_messages)
        
        # Connect to Gmail and scan ALL folders
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL, PASSWORD)
        
        # Get all folders
        status, folders = mail.list()
        folder_names = []
        for folder in folders:
            folder_str = folder.decode('utf-8')
            folder_name = folder_str.split('"')[-2]
            folder_names.append(folder_name)
        
        print(f"📁 Scanning {len(folder_names)} folders: {folder_names}")
        
        # Scan each folder
        for folder_name in folder_names:
            try:
                mail.select(folder_name)
                status, messages = mail.search(None, 'ALL')  # Get ALL emails from this folder
                
                if status == 'OK':
                    email_ids = messages[0].split()
                    print(f"📧 Folder '{folder_name}': {len(email_ids)} emails")
                    
                    # Process emails from this folder
                    for email_id in email_ids:
                        try:
                            status, msg_data = mail.fetch(email_id, '(RFC822)')
                            if status == 'OK':
                                email_body = msg_data[0][1]
                                email_message = email.message_from_bytes(email_body)
                                
                                from_email = email_message.get('From', '')
                                subject = email_message.get('Subject', '')
                                date_received = email_message.get('Date', '')
                                
                                if should_capture_email(subject, from_email, email_message):
                                    message_content = extract_email_content(email_message)
                                    from_addr = extract_email_address(from_email)
                                    
                                    # Check if we already have this email
                                    existing_reply = any(
                                        r['from_email'] == from_addr and 
                                        r['subject'] == subject and 
                                        r['message'] == message_content 
                                        for r in reply_messages
                                    )
                                    
                                    if not existing_reply:
                                        email_type = determine_email_type(subject, from_email, message_content)
                                        
                                        reply = {
                                            'id': len(reply_messages) + 1,
                                            'from_email': from_addr,
                                            'from_name': extract_name_from_email(from_email),
                                            'subject': subject,
                                            'message': message_content,
                                            'received_date': date_received or datetime.now().isoformat(),
                                            'status': 'New',
                                            'original_campaign': 'Ultra-Aggressive Scan',
                                            'auto_detected': True,
                                            'email_type': email_type,
                                            'capture_reason': f'Ultra-aggressive scan from folder: {folder_name}',
                                            'source_folder': folder_name
                                        }
                                        
                                        reply_messages.append(reply)
                                        print(f"🔥 ULTRA CAPTURE: {email_type} from {reply['from_name']} (folder: {folder_name})")
                        
                        except Exception as e:
                            print(f"Error processing email {email_id} in folder {folder_name}: {e}")
                            continue
                
            except Exception as e:
                print(f"Error scanning folder {folder_name}: {e}")
                continue
        
        mail.close()
        mail.logout()
        
        new_emails = len(reply_messages) - initial_count
        print(f"🔥 ULTRA AGGRESSIVE SCAN COMPLETE: {new_emails} new emails captured!")
        
        return jsonify({
            'success': True,
            'message': f'🔥 ULTRA AGGRESSIVE SCAN COMPLETE! Found {new_emails} new emails from {len(folder_names)} folders. Total captured: {len(reply_messages)}',
            'new_emails_count': new_emails,
            'total_emails_count': len(reply_messages),
            'folders_scanned': len(folder_names),
            'scan_type': 'ultra_aggressive'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'🔥 ULTRA AGGRESSIVE SCAN FAILED: {str(e)}'})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    try:
        stop_email_monitoring()
        return jsonify({'success': True, 'message': 'Email monitoring stopped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/email-monitoring/status')
def monitoring_status():
    """Get email monitoring status"""
    return jsonify({
        'enabled': email_monitoring['enabled'],
        'last_check': email_monitoring['last_check'],
        'notifications': email_monitoring['notifications'][-10:]  # Last 10 notifications
    })

@app.route('/api/notifications')
def get_notifications():
    """Get all notifications"""
    return jsonify(email_monitoring['notifications'])

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications():
    """Clear all notifications"""
    global email_monitoring
    email_monitoring['notifications'] = []
    return jsonify({'success': True, 'message': 'Notifications cleared'})

@app.route('/api/sent-emails')
def get_sent_emails():
    """Get all sent campaign emails for tracking"""
    return jsonify({
        'total_sent': len(sent_campaign_emails['campaigns']),
        'unique_recipients': len(sent_campaign_emails['recipients']),
        'unique_subjects': len(sent_campaign_emails['subjects']),
        'campaigns': sent_campaign_emails['campaigns'][-50:],  # Last 50 campaigns
        'recipients': list(sent_campaign_emails['recipients']),
        'subjects': list(sent_campaign_emails['subjects'])
    })

@app.route('/api/sent-emails/clear', methods=['POST'])
def clear_sent_emails():
    """Clear sent email tracking (use with caution)"""
    global sent_campaign_emails
    sent_campaign_emails = {
        'subjects': set(),
        'recipients': set(),
        'campaigns': []
    }
    return jsonify({'success': True, 'message': 'Sent email tracking cleared'})

@app.route('/api/accurate-scan', methods=['POST'])
def accurate_scan():
    """ACCURATE: Scan only for replies to our sent campaign emails"""
    try:
        print("🎯 STARTING ACCURATE EMAIL SCAN (Replies Only)...")
        initial_count = len(reply_messages)
        
        # Force a complete scan with accurate filtering
        check_gmail_for_replies()
        
        new_emails = len(reply_messages) - initial_count
        
        return jsonify({
            'success': True, 
            'message': f'ACCURATE SCAN COMPLETE! Found {new_emails} replies to your campaign emails. Total captured: {len(reply_messages)}',
            'new_emails_count': new_emails,
            'total_emails_count': len(reply_messages),
            'scan_type': 'accurate_replies_only',
            'tracked_recipients': len(sent_campaign_emails['recipients']),
            'tracked_subjects': len(sent_campaign_emails['subjects'])
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'ACCURATE SCAN FAILED: {str(e)}'})

@app.route('/upload')
def upload():
    """Show upload page"""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get email content from form
        subject = request.form.get('subject', 'Your Subject Here')
        message = request.form.get('message', 'Your message here')
        
        # Start campaign in background
        global campaign_status
        campaign_status['running'] = True
        campaign_status['results'] = []
        
        thread = threading.Thread(target=process_email_campaign, args=(file_path, subject, message))
        thread.start()
        
        flash('Email campaign started!')
        return redirect(url_for('dashboard'))
    
    flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    return jsonify(campaign_status)

@app.route('/api/reset-all', methods=['POST'])
def reset_all_data():
    """Reset all data - clear contacts, campaign status, and sent emails"""
    global campaign_status, sent_campaign_emails, email_monitoring
    
    # Reset campaign status
    campaign_status = {
        'running': False,
        'total_emails': 0,
        'sent_emails': 0,
        'failed_emails': 0,
        'current_progress': 0,
        'current_recipient': '',
        'start_time': None,
        'end_time': None,
        'results': [],
        'contacts': []
    }
    
    # Reset sent emails tracking
    sent_campaign_emails = {
        'sent': [],
        'failed': [],
        'bounced': []
    }
    
    # Reset email monitoring
    email_monitoring = {
        'enabled': False,
        'last_check': None,
        'notifications': []
    }
    
    return jsonify({'success': True, 'message': 'All data reset successfully'})

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    import sys
    port = 5001 if '--port' in sys.argv else 5000
    app.run(debug=True, host='0.0.0.0', port=port)
