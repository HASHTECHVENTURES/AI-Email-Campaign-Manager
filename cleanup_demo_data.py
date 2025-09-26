#!/usr/bin/env python3
"""
Demo Data Cleanup Script
This script will help clean up demo/test data from your email campaign system.
"""

import requests
import json

# Your Vercel deployment URL
BASE_URL = "https://ai-email-campaign-manager-861d.vercel.app"

def cleanup_demo_data():
    """Clean up demo data from the system"""
    print("🧹 Starting demo data cleanup...")
    
    try:
        # Get current contacts
        print("📋 Getting current contacts...")
        response = requests.get(f"{BASE_URL}/get-contacts")
        
        if response.status_code == 200:
            contacts = response.json()
            print(f"Found {len(contacts)} contacts")
            
            # Remove each contact
            for contact in contacts:
                email = contact.get('email')
                if email:
                    print(f"🗑️  Removing contact: {email}")
                    
                    # Try to remove the contact
                    try:
                        remove_response = requests.post(
                            f"{BASE_URL}/remove-contact",
                            headers={'Content-Type': 'application/json'},
                            json={'email': email}
                        )
                        
                        if remove_response.status_code == 200:
                            print(f"✅ Successfully removed {email}")
                        else:
                            print(f"❌ Failed to remove {email}: {remove_response.text}")
                            
                    except Exception as e:
                        print(f"❌ Error removing {email}: {str(e)}")
            
            # Clear sent emails tracking
            print("🧹 Clearing sent emails tracking...")
            try:
                clear_response = requests.post(f"{BASE_URL}/api/sent-emails/clear")
                if clear_response.status_code == 200:
                    print("✅ Sent emails tracking cleared")
                else:
                    print(f"❌ Failed to clear sent emails: {clear_response.text}")
            except Exception as e:
                print(f"❌ Error clearing sent emails: {str(e)}")
            
            # Clear notifications
            print("🧹 Clearing notifications...")
            try:
                notif_response = requests.post(f"{BASE_URL}/api/notifications/clear")
                if notif_response.status_code == 200:
                    print("✅ Notifications cleared")
                else:
                    print(f"❌ Failed to clear notifications: {notif_response.text}")
            except Exception as e:
                print(f"❌ Error clearing notifications: {str(e)}")
            
        else:
            print(f"❌ Failed to get contacts: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
    
    print("\n🎉 Demo data cleanup completed!")
    print("Your email campaign system is now clean and ready for real use.")

if __name__ == "__main__":
    cleanup_demo_data()
