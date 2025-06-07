from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime
import pandas as pd
import io
import weasyprint
from jinja2 import Template
import tempfile
import zipfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class VoucherData(BaseModel):
    voucher_id: str
    data: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

# Voucher HTML Template
VOUCHER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Hotel Booking Confirmation Voucher</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
        }
        
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #333;
        }
        
        .voucher-container {
            border: 2px solid #dc2626;
            padding: 20px;
            background: white;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .logo {
            background: linear-gradient(135deg, #dc2626, #fbbf24);
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .title {
            color: #666;
            font-size: 18px;
            font-weight: bold;
            margin: 15px 0;
        }
        
        .emergency-contact {
            background: #dc2626;
            color: white;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        
        .emergency-title {
            font-weight: bold;
            font-size: 14px;
            text-align: center;
            margin-bottom: 8px;
        }
        
        .emergency-text {
            font-size: 12px;
            text-align: center;
            margin-bottom: 10px;
        }
        
        .contact-info {
            display: flex;
            justify-content: space-between;
            background: #fbbf24;
            color: #000;
            padding: 8px 15px;
            border-radius: 3px;
            font-weight: bold;
            font-size: 12px;
        }
        
        .voucher-details {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .voucher-details td {
            padding: 8px 12px;
            border: 1px solid #ddd;
            font-size: 12px;
        }
        
        .label-cell {
            background: #bfdbfe;
            font-weight: bold;
            width: 200px;
            color: #1e40af;
        }
        
        .value-cell {
            background: #f8fafc;
        }
        
        .map-link {
            color: #2563eb;
            text-decoration: underline;
        }
        
        .cancellation-highlight {
            color: #dc2626;
            font-weight: bold;
        }
        
        .footer-note {
            margin-top: 30px;
            padding: 15px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 5px;
            color: #dc2626;
            font-size: 12px;
            text-align: center;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="voucher-container">
        <div class="header">
            <div class="logo">LGT HOTEL STAYS</div>
            <div class="title">PREPAID HOTEL CONFIRMATION VOUCHER</div>
        </div>
        
        <div class="emergency-contact">
            <div class="emergency-title">EMERGENCY CONTACT DETAILS (24/7 Support)</div>
            <div class="emergency-text">In case of any issues during check-in/check-out during your stay at the hotel, please get in touch with us on our India emergency contact numbers mentioned below.</div>
            <div class="contact-info">
                <span>Mr. Sandeep +91 7326091303</span>
                <span>Email: ops@lgthotelstays.com</span>
            </div>
        </div>
        
        <table class="voucher-details">
            <tr>
                <td class="label-cell">DATE VOUCHER ISSUED</td>
                <td class="value-cell">{{ date_voucher_issued }}</td>
            </tr>
            <tr>
                <td class="label-cell">CONFIRMATION NUMBER (S)</td>
                <td class="value-cell">{{ confirmation_number }}</td>
            </tr>
            <tr>
                <td class="label-cell">HOTEL NAME</td>
                <td class="value-cell">{{ hotel_name }}</td>
            </tr>
            <tr>
                <td class="label-cell">ADDRESS</td>
                <td class="value-cell">{{ address }}</td>
            </tr>
            <tr>
                <td class="label-cell">MAP LOCATION</td>
                <td class="value-cell"><a href="{{ map_location }}" class="map-link">{{ map_location }}</a></td>
            </tr>
            <tr>
                <td class="label-cell">HOTEL CONTACT NO.</td>
                <td class="value-cell">{{ hotel_contact_no }}</td>
            </tr>
            <tr>
                <td class="label-cell">LEAD PASSENGER NAME (S)</td>
                <td class="value-cell">{{ lead_passenger_name }}</td>
            </tr>
            <tr>
                <td class="label-cell">ROOM TYPE</td>
                <td class="value-cell">{{ room_type }}</td>
            </tr>
            <tr>
                <td class="label-cell">INCLUSIONS</td>
                <td class="value-cell">{{ inclusions }}</td>
            </tr>
            <tr>
                <td class="label-cell">NO OF ROOMS</td>
                <td class="value-cell">{{ no_of_rooms }}</td>
            </tr>
            <tr>
                <td class="label-cell">NO OF ADULTS</td>
                <td class="value-cell">{{ no_of_adults }}</td>
            </tr>
            <tr>
                <td class="label-cell">NO OF CHILDREN</td>
                <td class="value-cell">{{ no_of_children }}</td>
            </tr>
            <tr>
                <td class="label-cell">CHECK-IN DATE</td>
                <td class="value-cell">{{ check_in_date }}</td>
            </tr>
            <tr>
                <td class="label-cell">CHECK-OUT DATE</td>
                <td class="value-cell">{{ check_out_date }}</td>
            </tr>
            <tr>
                <td class="label-cell">DURATION</td>
                <td class="value-cell">{{ duration }}</td>
            </tr>
            <tr>
                <td class="label-cell">CANCELLATION POLICY</td>
                <td class="value-cell cancellation-highlight">{{ cancellation_policy }}</td>
            </tr>
            <tr>
                <td class="label-cell">BOOKED AND PAYABLE BY</td>
                <td class="value-cell">{{ booked_and_payable_by }}</td>
            </tr>
        </table>
        
        <div class="footer-note">
            This voucher is valid for the above specified services only. Any other extra service shall be paid by the client at the hotel.
        </div>
    </div>
</body>
</html>
"""

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hotel Voucher Generator API"}

@api_router.post("/upload-excel")
async def upload_excel_file(file: UploadFile = File(...)):
    """Upload and parse Excel file containing voucher data"""
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
        
        # Read the Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Convert DataFrame to list of dictionaries
        voucher_data = df.to_dict('records')
        
        # Clean and validate data
        processed_vouchers = []
        for i, row in enumerate(voucher_data):
            # Convert all values to strings and handle NaN values
            cleaned_row = {}
            for key, value in row.items():
                # Normalize key: lowercase, replace spaces and hyphens with underscores
                normalized_key = str(key).lower().replace(' ', '_').replace('-', '_')
                if pd.isna(value):
                    cleaned_row[normalized_key] = ""
                else:
                    cleaned_row[normalized_key] = str(value)
            
            processed_vouchers.append({
                "row_number": i + 1,
                "data": cleaned_row
            })
        
        return {
            "status": "success",
            "message": f"Successfully parsed {len(processed_vouchers)} voucher records",
            "vouchers": processed_vouchers,
            "columns": list(df.columns)
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")

@api_router.post("/generate-vouchers")
async def generate_vouchers(vouchers: List[Dict[str, Any]]):
    """Generate PDF vouchers from voucher data"""
    try:
        # Create temporary directory for PDFs
        temp_dir = tempfile.mkdtemp()
        pdf_files = []
        
        template = Template(VOUCHER_TEMPLATE)
        
        for i, voucher_data in enumerate(vouchers):
            # Map Excel column names to template variables
            template_data = map_excel_data_to_template(voucher_data.get('data', {}))
            
            # Render HTML
            html_content = template.render(**template_data)
            
            # Generate PDF
            pdf_filename = f"voucher_{i+1}_{template_data.get('confirmation_number', 'unknown')}.pdf"
            pdf_path = os.path.join(temp_dir, pdf_filename)
            
            weasyprint.HTML(string=html_content).write_pdf(pdf_path)
            pdf_files.append(pdf_path)
        
        # Create ZIP file containing all PDFs
        zip_filename = f"hotel_vouchers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pdf_file in pdf_files:
                zipf.write(pdf_file, os.path.basename(pdf_file))
        
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type='application/zip'
        )
        
    except Exception as e:
        logger.error(f"Error generating vouchers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating vouchers: {str(e)}")

def map_excel_data_to_template(data: Dict[str, Any]) -> Dict[str, str]:
    """Map Excel column data to template variables with fallbacks"""
    
    # Common mapping variations for Excel columns
    mapping = {
        'date_voucher_issued': ['date_voucher_issued', 'voucher_date', 'issue_date', 'created_date'],
        'confirmation_number': ['confirmation_number', 'booking_id', 'confirmation_id', 'booking_number'],
        'hotel_name': ['hotel_name', 'hotel', 'property_name'],
        'address': ['address', 'hotel_address', 'location'],
        'map_location': ['map_location', 'map_link', 'google_maps', 'location_link'],
        'hotel_contact_no': ['hotel_contact_no', 'hotel_phone', 'contact_number', 'phone'],
        'lead_passenger_name': ['lead_passenger_name', 'guest_name', 'primary_guest', 'name'],
        'room_type': ['room_type', 'room_category', 'accommodation_type'],
        'inclusions': ['inclusions', 'amenities', 'services_included'],
        'no_of_rooms': ['no_of_rooms', 'rooms', 'room_count'],
        'no_of_adults': ['no_of_adults', 'adults', 'adult_count'],
        'no_of_children': ['no_of_children', 'children', 'child_count', 'kids'],
        'check_in_date': ['check_in_date', 'checkin_date', 'arrival_date', 'check_in'],
        'check_out_date': ['check_out_date', 'checkout_date', 'departure_date', 'check_out'],
        'duration': ['duration', 'nights', 'stay_duration', 'number_of_nights'],
        'cancellation_policy': ['cancellation_policy', 'cancellation', 'policy'],
        'booked_and_payable_by': ['booked_and_payable_by', 'booked_by', 'agency', 'company']
    }
    
    result = {}
    
    for template_key, possible_columns in mapping.items():
        value = ""
        for col in possible_columns:
            if col in data and data[col]:
                value = str(data[col]).strip()
                break
        
        # Set default values for missing data
        if not value:
            if template_key == 'date_voucher_issued':
                value = datetime.now().strftime('%d-%b-%Y')
            elif template_key == 'booked_and_payable_by':
                value = 'LGT India'
            elif template_key == 'map_location':
                value = '#'
            elif template_key in ['no_of_children', 'no_of_rooms', 'no_of_adults']:
                value = '0'
            else:
                value = 'N/A'
        
        result[template_key] = value
    
    return result

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
