#!/usr/bin/env python3
"""
Simple test script to demonstrate the contact API
Run this after starting the server with: uvicorn app.main:app --reload
"""

import requests
import json

def test_contact_api():
    """Test the contact API endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/contact/"
    
    # Test data
    test_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "company": "Acme Corporation",
        "subject": "General Inquiry",
        "message": "Hello! I'm interested in learning more about your services. Please contact me at your earliest convenience."
    }
    
    try:
        # Make the request
        response = requests.post(url, json=test_data)
        
        # Check if successful
        if response.status_code == 200:
            print("✅ Contact API test successful!")
            print(f"Response: {response.json()}")
            print("\n📝 Check your console/terminal where the server is running to see the printed contact form data.")
        else:
            print(f"❌ API test failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("Make sure the server is running with: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    print("🧪 Testing Contact API...")
    print("=" * 50)
    test_contact_api() 