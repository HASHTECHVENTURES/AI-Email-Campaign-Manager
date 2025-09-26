#!/usr/bin/env python3

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Importing modules...")
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
    
    print("Loading environment variables...")
    # Load environment variables
    load_dotenv()
    
    print("Creating Flask app...")
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-here'
    
    print("Setting up configuration...")
    # Configuration
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    print("Setting up routes...")
    @app.route('/')
    def index():
        print("Index route called!")
        return render_template('index.html')
    
    @app.route('/test')
    def test():
        return 'Test route works!'
    
    print("Routes defined:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    print("Starting Flask app...")
    if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5006)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
