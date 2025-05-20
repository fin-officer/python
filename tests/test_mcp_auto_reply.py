#!/usr/bin/env python3

"""
Simple test script for the MCP auto-reply functionality
"""

import json
import sys

import requests

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test email data
TEST_EMAIL = {
    "from_email": "test@example.com",
    "to_email": "support@finofficer.com",
    "subject": "Question about financial services",
    "content": "Hello,\n\nI am interested in your financial services. Could you please provide more information about your accounting packages for small businesses? I currently have 5 employees and need help with monthly bookkeeping and tax filing.\n\nThank you,\nJohn",
    "received_date": "2025-05-20T00:20:00",
}


def test_api_health():
    """Test if the API is running"""
    print("Testing API health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure the application is running.")
        return False


def create_test_email():
    """Create a test email"""
    print("\nCreating test email...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/emails/process",
            json=TEST_EMAIL,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            print("✅ Test email created successfully")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ Failed to create test email: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating test email: {str(e)}")
        return False


def test_auto_reply(email_id=1):
    """Test the auto-reply functionality"""
    print(f"\nTesting auto-reply for email ID {email_id}...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/emails/{email_id}/auto-reply",
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            print("✅ Auto-reply generated successfully")
            result = response.json()
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
            print("\nAuto-reply content:")
            print(f"{result.get('content')}")
            return True
        else:
            print(f"❌ Failed to generate auto-reply: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing auto-reply: {str(e)}")
        return False


def main():
    """Main function to run all tests"""
    print("\n=== MCP Auto-Reply Test ===\n")

    # Check if the API is running
    if not test_api_health():
        sys.exit(1)

    # Create a test email
    if not create_test_email():
        sys.exit(1)

    # Test the auto-reply functionality
    if not test_auto_reply():
        sys.exit(1)

    print("\n✅ All tests passed successfully!")


if __name__ == "__main__":
    main()
