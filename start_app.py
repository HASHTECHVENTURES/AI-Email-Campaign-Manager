#!/usr/bin/env python3
"""
Startup script for the AI Email Campaign Manager
"""

import os
import sys
import subprocess

def main():
    print("🚀 Starting AI Email Campaign Manager...")
    print("📧 Email: karmaterra427@gmail.com")
    print("🤖 AI: Gemini AI configured")
    print("🌐 Server will start on http://localhost:5008")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('simple_working_app.py'):
        print("❌ Error: simple_working_app.py not found!")
        print("Please run this script from the project directory.")
        sys.exit(1)
    
    try:
        # Start the Flask application
        subprocess.run([sys.executable, 'simple_working_app.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
