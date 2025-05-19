#!/usr/bin/env python3

# Simple test script for the auto-reply functionality
# This script is designed to be run inside the Docker container

import requests
import json
import time
import sys

# Set up the base URL for the API
BASE_URL = "http://localhost:8000"

def print_colored(text, color="green"):
    """Print colored text to the console"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print_colored("✅ API is running", "green")
            return True
        else:
            print_colored(f"❌ API returned status code {response.status_code}", "red")
            return False
    except requests.exceptions.ConnectionError:
        print_colored("❌ Could not connect to the API. Make sure the application is running.", "red")
        return False

def create_test_email():
    """Create a test email in the system"""
    print_colored("\n📧 Creating test email...", "blue")
    
    email_data = {
        "from_email": "test@example.com",
        "to_email": "support@fin-officer.com",
        "subject": "Question about financial services",
        "content": "Hello,\n\nI am interested in your financial services. Could you please provide more information about your accounting packages for small businesses? I currently have 5 employees and need help with monthly bookkeeping and tax filing.\n\nThank you,\nJohn",
        "received_date": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/emails/process",
            json=email_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print_colored("✅ Test email created successfully", "green")
            print_colored(f"📄 Response: {json.dumps(response.json(), indent=2)}", "cyan")
            return True
        else:
            print_colored(f"❌ Failed to create test email: {response.status_code}", "red")
            print_colored(f"ud83dudcc4 Response: {response.text}", "red")
            return False
    except Exception as e:
        print_colored(f"❌ Error creating test email: {str(e)}", "red")
        return False

def get_latest_email_id():
    """Get the ID of the latest email in the system"""
    print_colored("\n🔍 Getting latest email ID...", "blue")
    
    try:
        # This is a simplified approach - in a real system, you might have an endpoint to list emails
        # For testing purposes, we'll just use ID 1 since we just created it
        return 1
    except Exception as e:
        print_colored(f"❌ Error getting latest email ID: {str(e)}", "red")
        return None

def test_auto_reply(email_id):
    """Test the auto-reply functionality"""
    print_colored(f"\n🤖 Testing auto-reply for email ID {email_id}...", "blue")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/emails/{email_id}/auto-reply",
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print_colored("✅ Auto-reply generated successfully", "green")
            result = response.json()
            print_colored(f"📄 Status: {result.get('status')}", "cyan")
            print_colored(f"📄 Message: {result.get('message')}", "cyan")
            print_colored("\n📝 Auto-reply content:", "yellow")
            print_colored(f"{result.get('content')}", "white")
            return True
        else:
            print_colored(f"❌ Failed to generate auto-reply: {response.status_code}", "red")
            print_colored(f"ud83dudcc4 Response: {response.text}", "red")
            return False
    except Exception as e:
        print_colored(f"❌ Error testing auto-reply: {str(e)}", "red")
        return False

def main():
    """Main function to run all tests"""
    print_colored("\n=== Email LLM Processor - Auto-Reply Test ===\n", "purple")
    
    # Check if the API is running
    if not check_api_health():
        sys.exit(1)
    
    # Create a test email
    if not create_test_email():
        sys.exit(1)
    
    # Get the latest email ID
    email_id = get_latest_email_id()
    if email_id is None:
        sys.exit(1)
    
    # Test the auto-reply functionality
    if not test_auto_reply(email_id):
        sys.exit(1)
    
    print_colored("\n✅ All tests passed successfully!", "green")

if __name__ == "__main__":
    main()
