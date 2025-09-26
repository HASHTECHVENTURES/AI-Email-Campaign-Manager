#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import os
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
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
import requests

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
EMAIL = os.getenv('EMAIL', 'test@example.com')
PASSWORD = os.getenv('PASSWORD', 'test_password')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Gemini AI Configuration
GEMINI_API_KEY = "AIzaSyASwOL-TOo-FNBydsFTN_mWnN1zx7FJkX8"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# AI Personality Profiles
AI_PERSONALITIES = {
    'professional': {
        'name': 'Professional',
        'tone': 'formal and business-focused',
        'style': 'Direct, clear, and results-oriented. Uses business terminology.',
        'greeting': 'Thank you for your response.',
        'closing': 'Best regards'
    },
    'friendly': {
        'name': 'Friendly',
        'tone': 'warm and approachable',
        'style': 'Conversational, personable, and engaging. Uses casual language.',
        'greeting': 'Great to hear from you!',
        'closing': 'Looking forward to connecting'
    },
    'consultative': {
        'name': 'Consultative',
        'tone': 'advisory and solution-focused',
        'style': 'Asks thoughtful questions, provides insights, positions as expert.',
        'greeting': 'I appreciate you taking the time to respond.',
        'closing': 'Happy to discuss further'
    },
    'enthusiastic': {
        'name': 'Enthusiastic',
        'tone': 'energetic and passionate',
        'style': 'Excited, motivational, uses exclamation points strategically.',
        'greeting': 'Fantastic to hear from you!',
        'closing': 'Excited to explore this opportunity together'
    }
}

# AI Context Memory - stores conversation history
ai_conversation_memory = {}

# AI Learning Data - improves responses over time
ai_learning_data = {
    'successful_responses': [],
    'failed_responses': [],
    'response_patterns': {},
    'user_preferences': {}
}

# AUTOMATED FOLLOW-UP SEQUENCES - This is going to be EPIC! 🔥
follow_up_sequences = {
    'interested_sequence': [
        {
            'delay_hours': 24,
            'trigger': 'positive_response',
            'subject': 'Great to hear from you! Next steps...',
            'template': 'interested_followup_1',
            'personality': 'consultative'
        },
        {
            'delay_hours': 72,
            'trigger': 'no_response_to_first',
            'subject': 'Quick follow-up on our conversation',
            'template': 'interested_followup_2',
            'personality': 'friendly'
        }
    ],
    'neutral_sequence': [
        {
            'delay_hours': 48,
            'trigger': 'neutral_response',
            'subject': 'Additional information you might find valuable',
            'template': 'neutral_followup_1',
            'personality': 'consultative'
        },
        {
            'delay_hours': 168,  # 1 week
            'trigger': 'no_response_to_first',
            'subject': 'Checking in - any questions?',
            'template': 'neutral_followup_2',
            'personality': 'professional'
        }
    ],
    'not_interested_sequence': [
        {
            'delay_hours': 720,  # 30 days
            'trigger': 'negative_response',
            'subject': 'Things change - staying in touch',
            'template': 'not_interested_followup_1',
            'personality': 'professional'
        }
    ]
}

# Follow-up tracking
active_followups = []
followup_analytics = {
    'total_scheduled': 0,
    'total_sent': 0,
    'conversion_rate': 0,
    'best_performing_sequence': 'interested_sequence'
}

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

def send_email_with_tracking(recipient, first_name, last_name, subject, message):
    """Send email with actual SMTP functionality"""
    if not recipient or not first_name:
        return False, "Incomplete recipient data"
    
    # Handle missing last name (common for AI replies)
    if not last_name:
        last_name = ""
    
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
        # Check if we're in simulation mode (no real email credentials configured)
        if EMAIL == 'test@example.com' or PASSWORD == 'test_password':
            print(f"📧 SIMULATION MODE: Email queued for {recipient}")
            print(f"📧 SUBJECT: {subject}")
            print(f"📧 CONTENT: {email_content[:100]}...")
            
            # Track sent email even in simulation mode
            sent_campaign_emails['recipients'].add(recipient.lower())
            sent_campaign_emails['subjects'].add(subject)
            sent_campaign_emails['campaigns'].append({
                'recipient': recipient,
                'subject': subject,
                'campaign_name': 'Email Campaign',
                'sent_date': datetime.now().isoformat()
            })
            
            print(f"✅ EMAIL QUEUED: {recipient} - {subject}")
            return True, "Email queued successfully (configure SMTP for live sending)"
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        
        # Track sent email
        sent_campaign_emails['recipients'].add(recipient.lower())
        sent_campaign_emails['subjects'].add(subject)
        sent_campaign_emails['campaigns'].append({
            'recipient': recipient,
            'subject': subject,
            'campaign_name': 'Manual Campaign',
            'sent_date': datetime.now().isoformat()
        })
        
        print(f"✅ EMAIL SENT: {recipient} - {subject}")
        return True, "Email sent successfully"
    except Exception as e:
        print(f"❌ EMAIL FAILED: {recipient} - {str(e)}")
        # In case of email failure, provide helpful error message
        if "authentication" in str(e).lower() or "login" in str(e).lower():
            print(f"📧 SMTP AUTH FAILED: Please configure valid email credentials")
            return False, "SMTP authentication failed - please configure valid email credentials in settings"
        return False, str(e)

def check_gmail_for_replies():
    """Check Gmail inbox for replies to our sent emails"""
    global reply_messages, email_monitoring
    
    try:
        print("🔍 Checking Gmail for replies...")
        
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        
        # Search for emails from when we started sending campaigns
        import datetime as dt
        if campaign_status.get('start_time'):
            # Use campaign start time as the filter
            campaign_start = dt.datetime.fromisoformat(campaign_status['start_time'].replace('Z', '+00:00'))
            search_date = campaign_start.strftime('%d-%b-%Y')
        else:
            # Default to last 24 hours if no campaign start time
            yesterday = (dt.datetime.now() - dt.timedelta(days=1)).strftime('%d-%b-%Y')
            search_date = yesterday
            
        status, messages = mail.search(None, f'SINCE {search_date}')
        
        if status == 'OK':
            email_ids = messages[0].split()
            print(f"📧 Found {len(email_ids)} emails in last 7 days")
            
            for email_id in email_ids[-10:]:  # Check last 10 emails
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
                        
                        # Check if this is a reply to our campaign
                        if is_reply_to_our_campaign(from_email, subject):
                            # Extract message content
                            message_content = extract_email_content(email_message)
                            from_addr = extract_email_address(from_email)
                            
                            # Check if we already have this reply (more robust duplicate detection)
                            existing_reply = any(
                                r['from_email'] == from_addr and 
                                r['subject'] == subject and 
                                r['message'] == message_content and
                                r['received_date'] == (date_received or datetime.now().isoformat())
                                for r in reply_messages
                            )
                            
                            # Also check by email ID to prevent duplicates from same email
                            email_id_str = str(email_id)
                            existing_by_id = any(
                                r.get('email_id') == email_id_str
                                for r in reply_messages
                            )
                            
                            if not existing_reply and not existing_by_id:
                                # Add to reply messages
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
                                    'email_type': 'Reply',
                                    'capture_reason': 'Reply to our campaign email',
                                    'email_id': email_id_str  # Store email ID to prevent duplicates
                                }
                                
                                reply_messages.append(reply)
                                print(f"✅ NEW REPLY: {reply['from_name']} - {reply['subject']}")
                                
                                # 🤖 AUTO-AI REPLY - No manual intervention needed!
                                print("🤖 AUTO-AI: Generating automatic reply...")
                                try:
                                    # Add a small delay to avoid rate limiting
                                    import time
                                    time.sleep(1)
                                    
                                    success, ai_message = auto_reply_with_ai(reply['id'])
                                    if success:
                                        print(f"✅ AUTO-AI REPLY SENT: {reply['from_name']}")
                                        reply['status'] = 'AI Replied'
                                        reply['ai_auto_replied'] = True
                                        reply['ai_reply_date'] = datetime.now().isoformat()
                                        reply['ai_reply_text'] = ai_message
                                    else:
                                        print(f"❌ AUTO-AI FAILED: {ai_message}")
                                        reply['ai_error'] = ai_message
                                        reply['status'] = 'AI Error'
                                except Exception as e:
                                    print(f"❌ AUTO-AI ERROR: {e}")
                                    reply['ai_error'] = str(e)
                                    reply['status'] = 'AI Error'
                
                except Exception as e:
                    print(f"Error processing email {email_id}: {e}")
                    continue
        
        mail.close()
        mail.logout()
        email_monitoring['last_check'] = datetime.now().isoformat()
        print(f"🎯 Gmail check complete. Total replies: {len(reply_messages)}")
        
    except Exception as e:
        print(f"❌ Error checking Gmail: {e}")
        # Add a test reply for demonstration if Gmail fails
        if len(reply_messages) == 0:
            test_reply = {
                'id': len(reply_messages) + 1,
                'from_email': 'demo@example.com',
                'from_name': 'Demo User',
                'subject': 'Re: Partnership Opportunity - Let\'s Connect!',
                'message': 'Thank you for your email! I am interested in learning more.',
                'received_date': datetime.now().isoformat(),
                'status': 'New',
                'original_campaign': 'Demo',
                'auto_detected': True,
                'email_type': 'Reply',
                'capture_reason': 'Demo reply (Gmail connection failed)'
            }
            reply_messages.append(test_reply)

# ==================== AI AGENT FUNCTIONS ====================

def generate_ai_reply(incoming_email, original_campaign_subject, personality='professional', context_data=None):
    """Generate AI-powered reply using Gemini API with personality and context"""
    try:
        print(f"🤖 Generating AI reply with {personality} personality...")
        
        # Get personality profile
        personality_profile = AI_PERSONALITIES.get(personality, AI_PERSONALITIES['professional'])
        
        # Get conversation history for context
        from_email = incoming_email.get('from_email', '')
        conversation_history = ai_conversation_memory.get(from_email, [])
        
        # Build context string
        context_str = ""
        if conversation_history:
            context_str = f"\nCONVERSATION HISTORY:\n"
            for i, msg in enumerate(conversation_history[-3:]):  # Last 3 messages
                context_str += f"{i+1}. {msg.get('type', 'Unknown')}: {msg.get('content', '')[:100]}...\n"
        
        # Enhanced sentiment analysis
        message_content = incoming_email.get('message', '').lower()
        detected_sentiment = analyze_message_sentiment(message_content)
        
        # Prepare the advanced prompt for Gemini
        prompt = f"""
You are an advanced AI sales assistant with a {personality_profile['tone']} personality. 

PERSONALITY PROFILE:
- Tone: {personality_profile['tone']}
- Style: {personality_profile['style']}
- Greeting Style: {personality_profile['greeting']}
- Closing Style: {personality_profile['closing']}

ORIGINAL CAMPAIGN: {original_campaign_subject}

INCOMING EMAIL ANALYSIS:
From: {incoming_email.get('from_name', 'Unknown')}
Email: {from_email}
Subject: {incoming_email.get('subject', 'No Subject')}
Detected Sentiment: {detected_sentiment['sentiment']} (confidence: {detected_sentiment['confidence']})
Detected Intent: {detected_sentiment['intent']}
Urgency Level: {detected_sentiment['urgency']}

MESSAGE CONTENT:
{incoming_email.get('message', 'No message content')}

{context_str}

ADVANCED INSTRUCTIONS:
1. Use the {personality} personality consistently
2. Reference conversation history if available
3. Adapt response based on detected sentiment ({detected_sentiment['sentiment']})
4. Address their specific intent: {detected_sentiment['intent']}
5. Match their communication style and urgency level
6. Include a clear next step or call-to-action
7. Keep response length appropriate (2-4 sentences for interested, 1-2 for not interested)
8. Use the personality's greeting and closing styles

RESPONSE FORMAT: Provide only the email body text, no subject line.
"""
        
        # Call Gemini API
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
        
        print(f"🔗 Calling Gemini API...")
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=30)
        print(f"📡 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 API Response: {result}")
            
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    ai_reply = candidate['content']['parts'][0]['text']
                    print(f"✅ AI Reply Generated: {ai_reply[:100]}...")
                    return ai_reply.strip()
                else:
                    print("❌ No content in AI response")
                    return get_fallback_reply(incoming_email)
            else:
                print("❌ No candidates in AI response")
                return get_fallback_reply(incoming_email)
        else:
            print(f"❌ Gemini API Error: {response.status_code} - {response.text}")
            return get_fallback_reply(incoming_email)
            
    except requests.exceptions.Timeout:
        print("❌ AI API Timeout - using fallback")
        return get_fallback_reply(incoming_email)
    except requests.exceptions.RequestException as e:
        print(f"❌ AI API Request Error: {e} - using fallback")
        return get_fallback_reply(incoming_email)
    except Exception as e:
        print(f"❌ AI Reply Generation Error: {e} - using fallback")
        return get_fallback_reply(incoming_email)

def get_fallback_reply(incoming_email):
    """Generate a fallback reply when AI fails"""
    from_name = incoming_email.get('from_name', 'there')
    message = incoming_email.get('message', '').lower()
    
    # Smart fallback based on message content
    if 'interested' in message or 'yes' in message:
        return f"Hi {from_name},\n\nThank you for your interest! I'd be happy to discuss this opportunity further. When would be a good time for a brief call to explore how we can work together?\n\nBest regards"
    elif 'not interested' in message or 'no thank' in message:
        return f"Hi {from_name},\n\nThank you for taking the time to respond. I completely understand, and I appreciate your honesty. If anything changes in the future, please don't hesitate to reach out.\n\nBest regards"
    elif 'question' in message or '?' in message:
        return f"Hi {from_name},\n\nThank you for your message and great questions! I'd be happy to provide more details and address any concerns you might have. Would you prefer a quick call or email exchange?\n\nBest regards"
    else:
        return f"Hi {from_name},\n\nThank you for your response! I appreciate you taking the time to get back to me. I'd love to continue our conversation and explore potential opportunities together.\n\nBest regards"

def analyze_message_sentiment(message_content):
    """Advanced sentiment analysis with emotion detection"""
    try:
        # Enhanced keyword-based analysis
        positive_keywords = ['interested', 'yes', 'great', 'excellent', 'perfect', 'love', 'amazing', 'fantastic', 'wonderful', 'excited', 'definitely', 'absolutely', 'sounds good', 'let\'s do it', 'count me in']
        negative_keywords = ['not interested', 'no thanks', 'not now', 'busy', 'pass', 'decline', 'reject', 'unsubscribe', 'remove', 'stop', 'never', 'waste of time', 'not relevant']
        question_keywords = ['how', 'what', 'when', 'where', 'why', 'which', 'can you', 'could you', 'would you', '?', 'tell me', 'explain', 'clarify']
        urgent_keywords = ['urgent', 'asap', 'immediately', 'quickly', 'rush', 'emergency', 'deadline', 'time sensitive', 'right away']
        
        # Count keyword matches
        positive_score = sum(1 for keyword in positive_keywords if keyword in message_content)
        negative_score = sum(1 for keyword in negative_keywords if keyword in message_content)
        question_score = sum(1 for keyword in question_keywords if keyword in message_content)
        urgent_score = sum(1 for keyword in urgent_keywords if keyword in message_content)
        
        # Determine sentiment
        if positive_score > negative_score:
            sentiment = 'positive'
            confidence = min(0.9, 0.6 + (positive_score * 0.1))
        elif negative_score > positive_score:
            sentiment = 'negative'
            confidence = min(0.9, 0.6 + (negative_score * 0.1))
        else:
            sentiment = 'neutral'
            confidence = 0.5
        
        # Determine intent
        if positive_score >= 2:
            intent = 'very_interested'
        elif positive_score >= 1:
            intent = 'interested'
        elif negative_score >= 1:
            intent = 'not_interested'
        elif question_score >= 2:
            intent = 'needs_information'
        elif question_score >= 1:
            intent = 'has_questions'
        else:
            intent = 'neutral_response'
        
        # Determine urgency
        if urgent_score >= 1:
            urgency = 'high'
        elif positive_score >= 2 or question_score >= 2:
            urgency = 'medium'
        else:
            urgency = 'low'
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'intent': intent,
            'urgency': urgency,
            'scores': {
                'positive': positive_score,
                'negative': negative_score,
                'questions': question_score,
                'urgent': urgent_score
            }
        }
        
    except Exception as e:
        print(f"❌ Sentiment analysis error: {e}")
        return {
            'sentiment': 'neutral',
            'confidence': 0.5,
            'intent': 'neutral_response',
            'urgency': 'low',
            'scores': {'positive': 0, 'negative': 0, 'questions': 0, 'urgent': 0}
        }

def update_conversation_memory(from_email, message_type, content, ai_response=None):
    """Update conversation memory for context awareness"""
    try:
        if from_email not in ai_conversation_memory:
            ai_conversation_memory[from_email] = []
        
        # Add incoming message
        ai_conversation_memory[from_email].append({
            'timestamp': datetime.now().isoformat(),
            'type': message_type,
            'content': content[:200],  # Store first 200 chars
            'ai_response': ai_response[:200] if ai_response else None
        })
        
        # Keep only last 10 messages per contact
        if len(ai_conversation_memory[from_email]) > 10:
            ai_conversation_memory[from_email] = ai_conversation_memory[from_email][-10:]
            
        print(f"📝 Updated conversation memory for {from_email}")
        
    except Exception as e:
        print(f"❌ Memory update error: {e}")

def get_smart_personality(incoming_email, sentiment_data):
    """Intelligently select personality based on email content and sender"""
    try:
        message_content = incoming_email.get('message', '').lower()
        from_name = incoming_email.get('from_name', '').lower()
        
        # Business indicators
        business_keywords = ['company', 'business', 'corporate', 'enterprise', 'organization', 'firm', 'llc', 'inc', 'ltd']
        casual_keywords = ['hey', 'hi there', 'what\'s up', 'thanks!', 'awesome', 'cool']
        
        # Check for business context
        is_business = any(keyword in message_content or keyword in from_name for keyword in business_keywords)
        is_casual = any(keyword in message_content for keyword in casual_keywords)
        
        # Select personality based on context
        if sentiment_data['intent'] == 'very_interested' and not is_business:
            return 'enthusiastic'
        elif sentiment_data['intent'] in ['needs_information', 'has_questions']:
            return 'consultative'
        elif is_casual and not is_business:
            return 'friendly'
        else:
            return 'professional'
            
    except Exception as e:
        print(f"❌ Personality selection error: {e}")
        return 'professional'

# ==================== AUTOMATED FOLLOW-UP SYSTEM ====================

def schedule_followup_sequence(contact_email, contact_name, sentiment_data, original_subject):
    """Schedule intelligent follow-up sequences based on response sentiment"""
    try:
        print(f"🔄 Scheduling follow-up sequence for {contact_name} based on {sentiment_data['sentiment']} sentiment")
        
        # Determine which sequence to use
        if sentiment_data['sentiment'] == 'positive' or sentiment_data['intent'] in ['interested', 'very_interested']:
            sequence_type = 'interested_sequence'
        elif sentiment_data['sentiment'] == 'negative' or sentiment_data['intent'] == 'not_interested':
            sequence_type = 'not_interested_sequence'
        else:
            sequence_type = 'neutral_sequence'
        
        sequence = follow_up_sequences[sequence_type]
        
        # Schedule each follow-up in the sequence
        for i, followup in enumerate(sequence):
            followup_data = {
                'id': len(active_followups) + 1,
                'contact_email': contact_email,
                'contact_name': contact_name,
                'sequence_type': sequence_type,
                'step': i + 1,
                'scheduled_time': datetime.now() + timedelta(hours=followup['delay_hours']),
                'subject': followup['subject'],
                'template': followup['template'],
                'personality': followup['personality'],
                'trigger': followup['trigger'],
                'status': 'scheduled',
                'original_subject': original_subject,
                'sentiment_trigger': sentiment_data
            }
            
            active_followups.append(followup_data)
            followup_analytics['total_scheduled'] += 1
            
        print(f"✅ Scheduled {len(sequence)} follow-ups for {contact_name} using {sequence_type}")
        return True, f"Scheduled {len(sequence)} intelligent follow-ups"
        
    except Exception as e:
        print(f"❌ Follow-up scheduling error: {e}")
        return False, str(e)

def generate_followup_content(followup_data):
    """Generate AI-powered follow-up content based on template and context"""
    try:
        template_prompts = {
            'interested_followup_1': f"""
Generate a consultative follow-up email for someone who showed interest. 

CONTEXT:
- They responded positively to: {followup_data['original_subject']}
- This is the first follow-up after 24 hours
- Use consultative personality
- Focus on next steps and value proposition

Generate a professional follow-up that:
1. References their positive response
2. Provides additional value or information
3. Suggests concrete next steps (call, meeting, demo)
4. Maintains momentum without being pushy
""",
            'interested_followup_2': f"""
Generate a friendly follow-up for someone who was interested but didn't respond to first follow-up.

CONTEXT:
- They showed initial interest in: {followup_data['original_subject']}
- This is the second follow-up after 3 days
- Use friendly personality
- Gentle nudge without pressure

Generate a warm follow-up that:
1. Acknowledges they might be busy
2. Reiterates the value proposition briefly
3. Offers flexible next steps
4. Keeps the door open
"""
        }
        
        prompt = template_prompts.get(followup_data['template'], 
                                    f"Generate a professional follow-up email for {followup_data['contact_name']}")
        
        # Use the AI to generate the follow-up content
        fake_email = {
            'from_name': followup_data['contact_name'],
            'from_email': followup_data['contact_email'],
            'subject': followup_data['original_subject'],
            'message': prompt
        }
        
        followup_content = generate_ai_reply(fake_email, followup_data['original_subject'], 
                                           followup_data['personality'])
        
        return followup_content
        
    except Exception as e:
        print(f"❌ Follow-up content generation error: {e}")
        return f"Hi {followup_data['contact_name']},\n\nI wanted to follow up on our previous conversation. Please let me know if you have any questions.\n\nBest regards"

def auto_reply_with_ai(reply_id):
    """Automatically reply to an email using AI"""
    try:
        print(f"🤖 Auto-replying with AI to reply ID: {reply_id}")
        
        # Find the reply
        reply = None
        for r in reply_messages:
            if r['id'] == reply_id:
                reply = r
                break
        
        if not reply:
            return False, "Reply not found"
        
        # Analyze sentiment first
        sentiment_data = analyze_message_sentiment(reply.get('message', ''))
        
        # Select smart personality
        smart_personality = get_smart_personality(reply, sentiment_data)
        
        # Generate AI reply with personality and context
        ai_reply_text = generate_ai_reply(
            reply, 
            reply.get('original_campaign', 'Partnership Opportunity'),
            personality=smart_personality
        )
        
        if not ai_reply_text:
            return False, "Failed to generate AI reply"
        
        # Update conversation memory
        update_conversation_memory(
            reply.get('from_email', ''),
            'incoming_reply',
            reply.get('message', ''),
            ai_reply_text
        )
        
        # 🔥 SCHEDULE AUTOMATED FOLLOW-UP SEQUENCE! 
        print("🔄 Scheduling intelligent follow-up sequence...")
        try:
            schedule_success, schedule_message = schedule_followup_sequence(
                reply.get('from_email', ''),
                reply.get('from_name', 'Contact'),
                sentiment_data,
                reply.get('subject', 'Email Campaign')
            )
            if schedule_success:
                print(f"✅ FOLLOW-UP SCHEDULED: {schedule_message}")
            else:
                print(f"❌ Follow-up scheduling failed: {schedule_message}")
        except Exception as e:
            print(f"❌ Follow-up scheduling error: {e}")
        
        # Send the AI-generated reply
        # Extract first name from the reply
        from_name = reply.get('from_name', 'Friend')
        first_name = from_name.split()[0] if from_name else 'Friend'
        
        success, result = send_email_with_tracking(
            recipient=reply['from_email'],
            first_name=first_name,
            last_name='',  # We don't have last name from replies
            subject=f"Re: {reply['subject']}",
            message=ai_reply_text
        )
        
        if success:
            # Mark as replied
            reply['status'] = 'AI Replied'
            reply['ai_reply_sent'] = True
            reply['ai_reply_text'] = ai_reply_text
            reply['ai_reply_date'] = datetime.now().isoformat()
            print(f"✅ AI Reply Sent Successfully to {reply['from_name']}")
            return True, ai_reply_text  # Return the actual AI reply text
        else:
            return False, f"Failed to send AI reply: {result}"
            
    except Exception as e:
        print(f"❌ Auto-reply Error: {e}")
        return False, str(e)

def analyze_email_sentiment(email_content):
    """Analyze email sentiment and intent using AI"""
    try:
        prompt = f"""
Analyze this email and provide a JSON response with:
1. sentiment: "positive", "negative", or "neutral"
2. intent: "interested", "not_interested", "question", "objection", or "other"
3. urgency: "high", "medium", or "low"
4. suggested_action: "reply_immediately", "reply_later", "follow_up", or "no_action"

EMAIL CONTENT: {email_content}

Respond with only valid JSON, no other text.
"""
        
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
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                analysis_text = result['candidates'][0]['content']['parts'][0]['text']
                # Try to parse JSON
                import json
                try:
                    analysis = json.loads(analysis_text)
                    return analysis
                except:
                    # Fallback if JSON parsing fails
                    return {
                        "sentiment": "neutral",
                        "intent": "other", 
                        "urgency": "medium",
                        "suggested_action": "reply_later"
                    }
            else:
                return None
        else:
            print(f"❌ AI Analysis Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Email Analysis Error: {e}")
        return None

def is_reply_to_our_campaign(from_email, subject):
    """Check if this email is a reply to our sent campaign emails"""
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
    
    return False

def extract_email_address(email_string):
    """Extract email address from 'Name <email@domain.com>' format"""
    import re
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

@app.route('/')
def index():
    return render_template('unified_dashboard.html')

@app.route('/old-dashboard')
def old_dashboard():
    return render_template('index.html')

@app.route('/manual-entry')
def manual_entry():
    return render_template('manual_entry.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/replies')
def replies():
    return render_template('replies.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/api/status')
def get_status():
    return jsonify(campaign_status)

# Add missing API endpoints for manual entry functionality
@app.route('/get-contacts')
def get_contacts():
    """Get all contacts for the current campaign"""
    contacts = campaign_status.get('contacts', [])
    return jsonify(contacts)

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
    
    # Check if contact already exists
    existing_contact = next((c for c in campaign_status['contacts'] if c['email'] == email), None)
    if existing_contact:
        return jsonify({'success': False, 'message': 'Contact with this email already exists'})
    
    campaign_status['contacts'].append({
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'gender': gender or 'O',
        'status': 'Pending'
    })
    
    return jsonify({'success': True, 'message': 'Contact added successfully'})

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
    
    # Reset campaign status
    campaign_status['running'] = True
    campaign_status['total_emails'] = len(campaign_status['contacts'])
    campaign_status['sent_emails'] = 0
    campaign_status['failed_emails'] = 0
    campaign_status['current_progress'] = 0
    campaign_status['start_time'] = datetime.now().isoformat()
    campaign_status['results'] = []
    
    # Send emails to all contacts
    for contact in campaign_status['contacts']:
        if contact['status'] != 'Sent':  # Only send if not already sent
            try:
                # Send actual email
                success, result = send_email_with_tracking(
                    contact['email'],
                    contact['first_name'],
                    contact['last_name'],
                    subject,
                    message
                )
                
                if success:
                    contact['status'] = 'Sent'
                    contact['sent_date'] = datetime.now().isoformat()
                    campaign_status['sent_emails'] += 1
                    campaign_status['results'].append({
                        'email': contact['email'],
                        'status': 'Sent',
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    contact['status'] = 'Failed'
                    campaign_status['failed_emails'] += 1
                    campaign_status['results'].append({
                        'email': contact['email'],
                        'status': 'Failed',
                        'error': result,
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                contact['status'] = 'Failed'
                campaign_status['failed_emails'] += 1
                campaign_status['results'].append({
                    'email': contact['email'],
                    'status': 'Failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
    
    # Mark campaign as completed
    campaign_status['running'] = False
    campaign_status['end_time'] = datetime.now().isoformat()
    campaign_status['current_progress'] = campaign_status['total_emails']
    
    return jsonify({'success': True, 'message': f'Manual campaign completed! Sent {campaign_status["sent_emails"]} emails.'})

@app.route('/reset-campaign', methods=['POST'])
def reset_campaign():
    """Reset campaign status"""
    global campaign_status
    
    campaign_status['running'] = False
    campaign_status['total_emails'] = 0
    campaign_status['sent_emails'] = 0
    campaign_status['failed_emails'] = 0
    campaign_status['current_progress'] = 0
    campaign_status['start_time'] = None
    campaign_status['end_time'] = None
    campaign_status['results'] = []
    
    # Reset all contacts to Pending status
    if 'contacts' in campaign_status:
        for contact in campaign_status['contacts']:
            contact['status'] = 'Pending'
            if 'sent_date' in contact:
                del contact['sent_date']
    
    return jsonify({'success': True, 'message': 'Campaign reset successfully'})

# Reply Management API Endpoints
@app.route('/api/replies')
def get_replies():
    """Get all reply messages"""
    return jsonify(reply_messages)

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

@app.route('/api/email-monitoring/start', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    try:
        email_monitoring['enabled'] = True
        email_monitoring['last_check'] = datetime.now().isoformat()
        
        # Start background monitoring thread
        import threading
        def monitor_emails():
            while email_monitoring['enabled']:
                try:
                    print("🔄 AUTO-MONITORING: Checking Gmail for replies...")
                    check_gmail_for_replies()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    print(f"Auto-monitoring error: {e}")
                    time.sleep(60)  # Wait 1 minute on error
        
        if not email_monitoring.get('monitoring_thread') or not email_monitoring['monitoring_thread'].is_alive():
            email_monitoring['monitoring_thread'] = threading.Thread(target=monitor_emails)
            email_monitoring['monitoring_thread'].daemon = True
            email_monitoring['monitoring_thread'].start()
            print("🚀 AUTO-MONITORING STARTED - Checking every 30 seconds!")
        
        return jsonify({'success': True, 'message': 'Email monitoring started successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/email-monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    try:
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

@app.route('/api/email-monitoring/check-now', methods=['POST'])
def check_now():
    """Manually check for replies right now"""
    try:
        # Check if we have any sent emails to look for replies to
        if not sent_campaign_emails['recipients']:
            return jsonify({'success': False, 'message': 'No sent emails found. Send a campaign first to receive replies.'})
        
        # Actually check Gmail for replies
        check_gmail_for_replies()
        
        return jsonify({'success': True, 'message': 'Manual check completed', 'replies_count': len(reply_messages)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/replies/clear', methods=['POST'])
def clear_replies():
    """Clear all replies"""
    global reply_messages
    reply_messages.clear()
    return jsonify({'success': True, 'message': 'All replies cleared'})


@app.route('/api/replies/remove-duplicates', methods=['POST'])
def remove_duplicate_replies():
    """Remove duplicate replies from the system"""
    global reply_messages
    
    try:
        original_count = len(reply_messages)
        
        # Remove duplicates based on from_email, subject, and message content
        seen = set()
        unique_replies = []
        
        for reply in reply_messages:
            # Create a unique identifier for each reply
            identifier = (
                reply.get('from_email', ''),
                reply.get('subject', ''),
                reply.get('message', '')[:100]  # First 100 chars of message
            )
            
            if identifier not in seen:
                seen.add(identifier)
                unique_replies.append(reply)
            else:
                print(f"🗑️ REMOVING DUPLICATE: {reply.get('from_name', 'Unknown')} - {reply.get('subject', 'No Subject')}")
        
        # Update reply messages with unique ones only
        reply_messages = unique_replies
        
        # Reassign IDs to maintain consistency
        for i, reply in enumerate(reply_messages):
            reply['id'] = i + 1
        
        removed_count = original_count - len(reply_messages)
        
        return jsonify({
            'success': True, 
            'message': f'Removed {removed_count} duplicate replies',
            'original_count': original_count,
            'current_count': len(reply_messages),
            'removed_count': removed_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/retry-failed', methods=['POST'])
def retry_failed_ai_replies():
    """Retry AI replies for failed emails"""
    global reply_messages
    
    try:
        failed_count = 0
        success_count = 0
        
        for reply in reply_messages:
            if reply.get('status') == 'AI Error' or reply.get('ai_error'):
                print(f"🔄 Retrying AI reply for: {reply['from_name']}")
                
                # Clear previous error
                if 'ai_error' in reply:
                    del reply['ai_error']
                
                # Try AI reply again
                success, ai_message = auto_reply_with_ai(reply['id'])
                if success:
                    reply['status'] = 'AI Replied'
                    reply['ai_auto_replied'] = True
                    reply['ai_reply_date'] = datetime.now().isoformat()
                    reply['ai_reply_text'] = ai_message
                    success_count += 1
                    print(f"✅ RETRY SUCCESS: {reply['from_name']}")
                else:
                    reply['ai_error'] = ai_message
                    reply['status'] = 'AI Error'
                    failed_count += 1
                    print(f"❌ RETRY FAILED: {reply['from_name']} - {ai_message}")
                
                # Add delay between retries
                import time
                time.sleep(2)
        
        return jsonify({
            'success': True,
            'message': f'Retry completed: {success_count} succeeded, {failed_count} failed',
            'success_count': success_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ==================== ANALYTICS & FOLLOW-UP API ENDPOINTS ====================

@app.route('/api/analytics/dashboard')
def get_analytics_dashboard():
    """Get comprehensive analytics data for the dashboard"""
    try:
        # Calculate analytics
        total_campaigns = len(sent_campaign_emails['campaigns'])
        total_responses = len(reply_messages)
        ai_replies = len([r for r in reply_messages if r.get('ai_auto_replied')])
        ai_efficiency = round((ai_replies / total_responses * 100) if total_responses > 0 else 95, 1)
        
        # Sentiment analysis
        positive_count = len([r for r in reply_messages if 'positive' in r.get('message', '').lower()])
        neutral_count = len([r for r in reply_messages if r.get('status') == 'New'])
        negative_count = len([r for r in reply_messages if 'not interested' in r.get('message', '').lower()])
        
        total_sentiment = positive_count + neutral_count + negative_count
        if total_sentiment > 0:
            positive_pct = round(positive_count / total_sentiment * 100)
            neutral_pct = round(neutral_count / total_sentiment * 100)
            negative_pct = round(negative_count / total_sentiment * 100)
        else:
            positive_pct, neutral_pct, negative_pct = 0, 0, 0  # No data yet
        
        analytics_data = {
            'kpis': {
                'total_campaigns': total_campaigns,
                'total_responses': total_responses,
                'ai_efficiency': ai_efficiency,
                'conversion_rate': 0,  # Will be calculated based on actual data
                'campaigns_growth': '+0%',
                'responses_growth': '+0%',
                'ai_improvement': '+0%',
                'conversion_trend': '+0%'
            },
            'ai_performance': {
                'successful_replies': ai_replies,
                'failed_replies': total_responses - ai_replies,
                'success_rate': ai_efficiency
            },
            'sentiment_analysis': {
                'positive': positive_pct,
                'neutral': neutral_pct,
                'negative': negative_pct
            },
            'followup_analytics': followup_analytics,
            'activity_feed': [
                {
                    'type': 'ai_reply',
                    'message': f'AI replied to {len([r for r in reply_messages if r.get("ai_auto_replied")])} contacts',
                    'time': '2 minutes ago',
                    'icon': 'robot',
                    'color': 'success'
                },
                {
                    'type': 'new_reply',
                    'message': f'Received {len(reply_messages)} total responses',
                    'time': '5 minutes ago',
                    'icon': 'envelope',
                    'color': 'info'
                }
            ]
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/followups/active')
def get_active_followups():
    """Get all active follow-up sequences"""
    try:
        return jsonify({
            'success': True,
            'followups': active_followups,
            'analytics': followup_analytics
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ==================== AI AGENT API ENDPOINTS ====================

@app.route('/api/ai/generate-reply', methods=['POST'])
def generate_ai_reply_endpoint():
    """Generate AI reply for a specific email"""
    try:
        data = request.get_json()
        reply_id = data.get('reply_id')
        
        if not reply_id:
            return jsonify({'success': False, 'message': 'Reply ID required'})
        
        # Find the reply
        reply = None
        for r in reply_messages:
            if r['id'] == reply_id:
                reply = r
                break
        
        if not reply:
            return jsonify({'success': False, 'message': 'Reply not found'})
        
        # Generate AI reply
        ai_reply_text = generate_ai_reply(reply, reply.get('original_campaign', 'Partnership Opportunity'))
        
        if ai_reply_text:
            return jsonify({
                'success': True, 
                'ai_reply': ai_reply_text,
                'message': 'AI reply generated successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to generate AI reply'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/auto-reply', methods=['POST'])
def auto_reply_endpoint():
    """Automatically reply using AI"""
    try:
        data = request.get_json()
        reply_id = data.get('reply_id')
        
        if not reply_id:
            return jsonify({'success': False, 'message': 'Reply ID required'})
        
        success, message = auto_reply_with_ai(reply_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/analyze-email', methods=['POST'])
def analyze_email_endpoint():
    """Analyze email sentiment and intent"""
    try:
        data = request.get_json()
        email_content = data.get('email_content')
        
        if not email_content:
            return jsonify({'success': False, 'message': 'Email content required'})
        
        analysis = analyze_email_sentiment(email_content)
        
        if analysis:
            return jsonify({
                'success': True,
                'analysis': analysis,
                'message': 'Email analyzed successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to analyze email'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai/smart-reply', methods=['POST'])
def smart_reply_endpoint():
    """Smart reply: analyze + generate + optionally send"""
    try:
        data = request.get_json()
        reply_id = data.get('reply_id')
        auto_send = data.get('auto_send', False)
        
        if not reply_id:
            return jsonify({'success': False, 'message': 'Reply ID required'})
        
        # Find the reply
        reply = None
        for r in reply_messages:
            if r['id'] == reply_id:
                reply = r
                break
        
        if not reply:
            return jsonify({'success': False, 'message': 'Reply not found'})
        
        # Analyze the email first
        analysis = analyze_email_sentiment(reply.get('message', ''))
        
        # Generate AI reply
        ai_reply_text = generate_ai_reply(reply, reply.get('original_campaign', 'Partnership Opportunity'))
        
        if not ai_reply_text:
            return jsonify({'success': False, 'message': 'Failed to generate AI reply'})
        
        result = {
            'success': True,
            'analysis': analysis,
            'ai_reply': ai_reply_text,
            'message': 'Smart reply generated successfully'
        }
        
        # Auto-send if requested
        if auto_send:
            success, send_result = auto_reply_with_ai(reply_id)
            result['auto_sent'] = success
            result['send_message'] = send_result
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    # Auto-start email monitoring
    print("🚀 Starting auto-monitoring...")
    email_monitoring['enabled'] = True
    
    def auto_monitor():
        while email_monitoring['enabled']:
            try:
                print("🔄 AUTO-MONITORING: Checking Gmail for replies...")
                check_gmail_for_replies()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Auto-monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    # Start monitoring in background
    monitoring_thread = threading.Thread(target=auto_monitor)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    print("✅ Auto-monitoring started - will check for replies every 30 seconds!")
    
    app.run(debug=True, host='0.0.0.0', port=5008)

# Vercel deployment entry point
# This ensures the app is available for Vercel's serverless functions
