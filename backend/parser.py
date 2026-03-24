import os
import io
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# Real OCR imports
import pytesseract
import fitz  # PyMuPDF
from PIL import Image

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# NOTE TO WINDOWS USERS:
# You must install Tesseract-OCR and uncomment the line below if it's not in your PATH.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_raw_text(file_bytes: bytes, content_type: str) -> str:
    """Uses real OCR to extract raw messy text from PDFs or Images."""
    text = ""
    try:
        if "pdf" in content_type.lower():
            # Convert PDF pages to images using PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            # Limit to first 2 pages for speed in MVP
            for page_num in range(min(2, len(doc))):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))
                text += pytesseract.image_to_string(image) + "\n"
        else:
            # Direct image OCR
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"OCR Error: {e}")
        return ""

def extract_invoice_data(file_bytes: bytes, content_type: str) -> dict:
    """The new pipeline: OCR -> LLM Cleanup -> JSON."""
    # 1. Real OCR Extraction
    raw_text = extract_raw_text(file_bytes, content_type)
    
    if isinstance(raw_text, dict):
        return raw_text # Return mock directly
        logging.warning("TESSERACT NOT FOUND. FALLING BACK TO MOCK DATA FOR DEMO.")
        return {
            "seller_gstin": "27AAECC4555A1Z1",
            "seller_name": "DEMO ENTERPRISE LTD",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-03-24",
            "subtotal": 1000.0,
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0.0,
            "total": 1180.0,
            "status": "completed",
            "note": "FALLBACK MOCK DATA"
        }

    # 2. Smart LLM Cleanup (Fast Tier)
    prompt = f"""You are a strict JSON data extractor. Extract invoice data from the noisy OCR text below.
Return ONLY a valid JSON object with EXACTLY these keys:
"seller_gstin" (string or null), "seller_name" (string or null), "invoice_number" (string or null), "invoice_date" (string or null), "total" (number or null), "cgst" (number or null), "sgst" (number or null), "igst" (number or null)

Raw OCR Text:
{raw_text[:3000]}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300
        )
        
        # 3. Clean and return JSON
        raw_json = response.choices[0].message.content
        start_idx = raw_json.find('{')
        end_idx = raw_json.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in response")
            
        cleaned_json = raw_json[start_idx:end_idx+1]
        data = json.loads(cleaned_json)
        data["status"] = "completed"
        return data
    except Exception as e:
        logging.error(f"LLM Parsing Error: {e}")
        return {"status": "failed", "error": "Failed to parse OCR text into structured data."}
