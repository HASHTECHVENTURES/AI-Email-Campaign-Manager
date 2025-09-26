#!/usr/bin/env python3
"""
AGGRESSIVE EMAIL CAPTURE SYSTEM STARTUP SCRIPT
==============================================

This script starts the enhanced email capture system with aggressive monitoring.
It will:
1. Start the Flask web application
2. Begin aggressive email monitoring
3. Provide access to the control interface

Usage:
    python start_aggressive_email_system.py

Access the control interface at: http://localhost:5000/aggressive-email-control
"""

import os
import sys
import time
import threading
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🔥 AGGRESSIVE EMAIL CAPTURE SYSTEM 🔥                ║
    ║                                                              ║
    ║  🎯 Enhanced Features:                                       ║
    ║     • 30-day email scanning (vs 7 days)                     ║
    ║     • ALL emails captured (vs 10 limit)                     ║
    ║     • 15-second monitoring (vs 30 seconds)                  ║
    ║     • Smart email classification                             ║
    ║     • Ultra-aggressive folder scanning                       ║
    ║     • Real-time notifications                                ║
    ║                                                              ║
    ║  🚀 Starting system...                                       ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if environment variables are set"""
    print("🔍 Checking environment configuration...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    
    if not email or not password:
        print("❌ ERROR: Missing Gmail credentials!")
        print("Please create a .env file with:")
        print("EMAIL=your_email@gmail.com")
        print("PASSWORD=your_app_password")
        print("\nTo get an app password:")
        print("1. Go to https://myaccount.google.com/apppasswords")
        print("2. Generate a new app password for 'Mail'")
        print("3. Use that password in your .env file")
        return False
    
    print(f"✅ Gmail account configured: {email}")
    return True

def start_aggressive_monitoring():
    """Start the aggressive email monitoring in background"""
    print("🚀 Starting aggressive email monitoring...")
    
    try:
        from app import start_email_monitoring
        start_email_monitoring()
        print("✅ Aggressive monitoring started successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to start monitoring: {e}")
        return False

def run_test_scan():
    """Run a test scan to verify everything works"""
    print("🧪 Running test scan...")
    
    try:
        from app import check_gmail_for_replies, reply_messages
        initial_count = len(reply_messages)
        check_gmail_for_replies()
        final_count = len(reply_messages)
        new_emails = final_count - initial_count
        
        print(f"✅ Test scan completed! Found {new_emails} new emails.")
        print(f"📊 Total emails captured: {final_count}")
        
        if new_emails > 0:
            print("\n📋 Recent emails:")
            for email in reply_messages[-min(3, new_emails):]:
                print(f"  • {email.get('email_type', 'Unknown')}: {email['from_name']} - {email['subject']}")
        
        return True
    except Exception as e:
        print(f"❌ Test scan failed: {e}")
        return False

def start_web_server():
    """Start the Flask web server"""
    print("🌐 Starting web server...")
    
    try:
        from app import app
        print("✅ Web server starting...")
        print("\n" + "="*60)
        print("🎯 AGGRESSIVE EMAIL CAPTURE SYSTEM IS READY!")
        print("="*60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🌐 Access URLs:")
        print("   • Main Dashboard: http://localhost:5000")
        print("   • 🔥 AGGRESSIVE CONTROL: http://localhost:5000/aggressive-email-control")
        print("   • Email Replies: http://localhost:5000/replies")
        print("   • Analytics: http://localhost:5000/analytics")
        print("\n🎮 Control Features:")
        print("   • Start/Stop monitoring")
        print("   • Aggressive scan (30 days, all emails)")
        print("   • Ultra-aggressive scan (all folders)")
        print("   • Real-time email capture")
        print("   • Smart email classification")
        print("\n⚡ Monitoring Status: ACTIVE (checking every 15 seconds)")
        print("="*60)
        
        # Start the Flask app
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        
    except Exception as e:
        print(f"❌ Failed to start web server: {e}")
        return False

def main():
    """Main startup function"""
    print_banner()
    
    # Check environment
    if not check_environment():
        return
    
    # Start aggressive monitoring
    if not start_aggressive_monitoring():
        print("⚠️  Warning: Monitoring failed to start, but continuing...")
    
    # Run test scan
    print("\n" + "="*40)
    if run_test_scan():
        print("✅ System test passed!")
    else:
        print("⚠️  System test failed, but continuing...")
    
    print("="*40)
    
    # Start web server (this will block)
    start_web_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down aggressive email capture system...")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
