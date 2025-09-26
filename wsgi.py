"""
WSGI Entry Point for Vercel Deployment
Email Campaign Manager - Professional Marketing Platform
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from simple_working_app import app

# Vercel expects the app to be available at module level
application = app

# This is the entry point for Vercel serverless functions
def handler(event, context):
    return app

if __name__ == "__main__":
    app.run()
