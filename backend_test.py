import requests
import sys
import json
from datetime import datetime

class MIND14APITester:
    def __init__(self, base_url="https://f6929cf2-bdfe-47f0-9996-3afbd187e5f8.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.conversation_id = None
        self.session_data = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        
        if headers:
            default_headers.update(headers)
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_services_endpoint(self):
        """Test the services endpoint"""
        success, response = self.run_test(
            "Services Endpoint",
            "GET",
            "services",
            200
        )
        if success:
            print(f"Found {len(response)} services")
            for service in response:
                print(f"  - {service['name']['en']} ({service['id']})")
        return success

    def test_chat_endpoint_english(self):
        """Test the chat endpoint with English message"""
        data = {
            "message": "Hello, I need help with health card renewal",
            "language": "en",
            "attachments": []
        }
        
        success, response = self.run_test(
            "Chat Endpoint (English)",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success:
            self.conversation_id = response.get('conversation_id')
            self.session_data = response.get('session_data')
            print(f"Conversation ID: {self.conversation_id}")
            print(f"Intent detected: {response.get('intent')} (confidence: {response.get('confidence', 0):.2f})")
            print(f"Response: {response.get('message')[:100]}...")
        
        return success

    def test_chat_endpoint_arabic(self):
        """Test the chat endpoint with Arabic message"""
        data = {
            "message": "مرحبا، أحتاج مساعدة في تجديد البطاقة الصحية",
            "language": "ar",
            "attachments": []
        }
        
        success, response = self.run_test(
            "Chat Endpoint (Arabic)",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success:
            print(f"Conversation ID: {response.get('conversation_id')}")
            print(f"Intent detected: {response.get('intent')} (confidence: {response.get('confidence', 0):.2f})")
            print(f"Response: {response.get('message')[:100]}...")
        
        return success

    def test_chat_continuation(self):
        """Test continuing a conversation"""
        if not self.conversation_id:
            print("❌ Cannot test conversation continuation - no conversation ID")
            return False
            
        data = {
            "message": "Yes, I want to proceed with this service",
            "conversation_id": self.conversation_id,
            "language": "en",
            "attachments": []
        }
        
        success, response = self.run_test(
            "Chat Continuation",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success:
            self.session_data = response.get('session_data')
            print(f"Session step: {self.session_data.get('step')}")
            print(f"Response: {response.get('message')[:100]}...")
        
        return success

    def test_booking_flow(self):
        """Test the booking flow"""
        if not self.conversation_id:
            print("❌ Cannot test booking flow - no conversation ID")
            return False
            
        # Step 1: Provide name
        data = {
            "message": "John Doe",
            "conversation_id": self.conversation_id,
            "language": "en",
            "attachments": []
        }
        
        success1, response1 = self.run_test(
            "Booking Flow - Name",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if not success1:
            return False
            
        # Step 2: Provide phone number
        data = {
            "message": "+1234567890",
            "conversation_id": self.conversation_id,
            "language": "en",
            "attachments": []
        }
        
        success2, response2 = self.run_test(
            "Booking Flow - Phone",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if not success2:
            return False
            
        # Step 3: Provide date and time
        data = {
            "message": "Tomorrow at 10:00 AM",
            "conversation_id": self.conversation_id,
            "language": "en",
            "attachments": []
        }
        
        success3, response3 = self.run_test(
            "Booking Flow - Date/Time",
            "POST",
            "chat",
            200,
            data=data
        )
        
        if success3:
            print(f"Booking completed: {response3.get('session_data', {}).get('step') == 'completed'}")
            print(f"Appointment ID: {response3.get('session_data', {}).get('appointment_id')}")
        
        return success3

    def test_automation_stats_endpoint(self):
        """Test the automation stats endpoint"""
        success, response = self.run_test(
            "Automation Stats Endpoint",
            "GET",
            "automation/stats",
            200
        )
        
        if success:
            print(f"Total Bookings: {response.get('totalBookings')}")
            print(f"Success Rate: {response.get('successRate')}%")
            print(f"Integration Status: {len(response.get('integrationStatus', {}))} integrations")
        
        return success

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting MIND14 Virtual Front Desk API Tests")
        print("=" * 60)
        
        # Basic endpoints
        self.test_root_endpoint()
        self.test_services_endpoint()
        
        # Chat endpoints
        self.test_chat_endpoint_english()
        self.test_chat_endpoint_arabic()
        self.test_chat_continuation()
        
        # Booking flow
        self.test_booking_flow()
        
        # Automation endpoints
        self.test_automation_stats_endpoint()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run} ({self.tests_passed/self.tests_run*100:.1f}%)")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = MIND14APITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)