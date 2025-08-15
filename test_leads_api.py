#!/usr/bin/env python3
"""
Test script for the leads API with simple Excel format
Run this after starting the server with: uvicorn app.main:app --reload
"""

import requests
import json
import pandas as pd
import io

def test_leads_api():
    """Test the leads API endpoints"""
    
    base_url = "http://localhost:8000/api/v1/leads"
    
    print("🧪 Testing Leads API...")
    print("=" * 50)
    
    # Test 1: Get all leads
    print("1. Testing GET /leads/")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            leads = response.json()
            print(f"✅ Retrieved {len(leads)} leads from database")
        else:
            print(f"❌ Failed to get leads: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 2: Create sample Excel file
    print("2. Creating sample Excel file...")
    sample_data = {
        'first_name': ['John', 'Jane', 'Bob', 'Alice'],
        'last_name': ['Doe', 'Smith', 'Johnson', 'Brown'],
        'phone_number': ['+1234567890', '+1234567891', '+1234567892', '+1234567893'],
        'call_pass': [True, False, True, False],
        'booking_success': [True, True, False, False]
    }
    
    df = pd.DataFrame(sample_data)
    
    # Save to Excel file
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    
    print("✅ Sample Excel file created with columns:")
    print(f"   {list(df.columns)}")
    print()
    
    # Test 3: Upload Excel file
    print("3. Testing Excel upload...")
    try:
        files = {'file': ('test_leads.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(f"{base_url}/upload-excel", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Excel upload successful!")
            print(f"   Leads processed: {result['leads_processed']}")
            print(f"   Leads saved: {result['leads_saved']}")
            if result.get('errors'):
                print(f"   Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:  # Show first 3 errors
                    print(f"     - {error}")
        else:
            print(f"❌ Excel upload failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error uploading Excel: {e}")
    
    print()
    
    # Test 4: Bulk create via JSON
    print("4. Testing bulk JSON creation...")
    try:
        bulk_data = {
            "leads": [
                {
                    "first_name": "Test",
                    "last_name": "User",
                    "phone_number": "+1234567899",
                    "call_pass": True,
                    "booking_success": False
                }
            ]
        }
        
        response = requests.post(f"{base_url}/bulk", json=bulk_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Bulk creation successful!")
            print(f"   Leads processed: {result['leads_processed']}")
            print(f"   Leads saved: {result['leads_saved']}")
        else:
            print(f"❌ Bulk creation failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error with bulk creation: {e}")
    
    print()
    print("=" * 50)
    print("🎉 Leads API testing completed!")

if __name__ == "__main__":
    test_leads_api() 