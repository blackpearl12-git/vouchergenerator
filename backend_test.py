
import requests
import os
import sys
import pandas as pd
import io
import tempfile
import zipfile
import time
from datetime import datetime

class HotelVoucherAPITester:
    def __init__(self, base_url="https://295c99a6-bf71-49f8-88f6-2a7823031d7d.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.headers.get('content-type') == 'application/json':
                    return success, response.json()
                return success, response
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.headers.get('content-type') == 'application/json':
                    print(f"Response: {response.json()}")
                return False, response

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, None

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        if success:
            print(f"Response: {response}")
        return success

    def create_sample_excel(self):
        """Create a sample Excel file with hotel booking data"""
        print("\n📊 Creating sample Excel file...")
        
        # Sample data based on the requirements
        data = {
            "Confirmation Number": ["399458300"],
            "Hotel Name": ["Novotel Dubai Al Barsha 4*"],
            "Lead Passenger Name": ["Mr PHILIP BENZIGAR"],
            "Address": ["Sheikh Zayed Rd - opp. InsuranceMarket Metro Station - Al Barsha - Al Barsha 1 - Dubai - United Arab Emirates"],
            "Check-in Date": ["08-May-2025 / 02 PM"],
            "Check-out Date": ["14-May-2025 / 11 AM"],
            "Room Type": ["Superior Double Room"],
            "No of Rooms": ["01"],
            "No of Adults": ["01"],
            "No of Children": ["0"],
            "Duration": ["06 Nights"],
            "Inclusions": ["Breakfast & Wi-Fi"],
            "Hotel Contact No": ["+971 4 304 9000"],
            "Cancellation Policy": ["Free cancellation before 07 May 2025 11:59 AM"]
        }
        
        df = pd.DataFrame(data)
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        temp_file.close()
        
        # Save DataFrame to Excel
        df.to_excel(temp_file.name, index=False)
        
        print(f"✅ Sample Excel file created at: {temp_file.name}")
        return temp_file.name

    def test_upload_excel(self, excel_file_path):
        """Test the upload-excel endpoint"""
        with open(excel_file_path, 'rb') as f:
            files = {'file': ('test_booking.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            success, response = self.run_test(
                "Upload Excel File",
                "POST",
                "upload-excel",
                200,
                files=files
            )
            
            if success:
                print(f"Parsed {len(response['vouchers'])} voucher records")
                return success, response['vouchers']
            return False, None

    def test_generate_vouchers(self, vouchers):
        """Test the generate-vouchers endpoint"""
        success, response = self.run_test(
            "Generate Vouchers",
            "POST",
            "generate-vouchers",
            200,
            data=vouchers
        )
        
        if success:
            # Save the ZIP file
            temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            temp_zip.write(response.content)
            temp_zip.close()
            
            print(f"✅ Vouchers ZIP file saved to: {temp_zip.name}")
            
            # Verify ZIP file contains PDFs
            try:
                with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                    pdf_files = zip_ref.namelist()
                    print(f"ZIP file contains {len(pdf_files)} PDF files:")
                    for pdf in pdf_files:
                        print(f"  - {pdf}")
                    return len(pdf_files) > 0
            except Exception as e:
                print(f"❌ Error verifying ZIP file: {str(e)}")
                return False
        return False

    def test_invalid_file_upload(self):
        """Test uploading an invalid file type"""
        # Create a temporary text file
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.write(b"This is not an Excel file")
        temp_file.close()
        
        with open(temp_file.name, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            success, response = self.run_test(
                "Upload Invalid File Type",
                "POST",
                "upload-excel",
                400,  # Expecting a 400 Bad Request
                files=files
            )
            
            os.unlink(temp_file.name)
            return success

    def print_summary(self):
        """Print a summary of the test results"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        if self.tests_passed == self.tests_run:
            print("✅ All tests passed!")
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")

def main():
    # Get the backend URL from environment or use default
    backend_url = "https://295c99a6-bf71-49f8-88f6-2a7823031d7d.preview.emergentagent.com"
    
    print(f"🔍 Testing Hotel Voucher Generator API at: {backend_url}")
    
    tester = HotelVoucherAPITester(backend_url)
    
    # Test root endpoint
    if not tester.test_root_endpoint():
        print("❌ Root endpoint test failed, stopping tests")
        tester.print_summary()
        return 1
    
    # Use the existing sample Excel file
    excel_file = "/app/sample_hotel_bookings.xlsx"
    if not os.path.exists(excel_file):
        print(f"❌ Sample Excel file not found at {excel_file}")
        tester.print_summary()
        return 1
    
    print(f"✅ Using sample Excel file: {excel_file}")
    
    # Test uploading Excel file
    upload_success, vouchers = tester.test_upload_excel(excel_file)
    if not upload_success:
        print("❌ Excel upload test failed, stopping tests")
        tester.print_summary()
        return 1
    
    # Test generating vouchers
    if not tester.test_generate_vouchers(vouchers):
        print("❌ Voucher generation test failed")
    
    # Test invalid file upload
    tester.test_invalid_file_upload()
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
