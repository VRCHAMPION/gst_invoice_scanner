import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
import PIL.Image
import io

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_invoice_data(file_bytes: bytes, content_type: str):
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Convert bytes to image
    image = PIL.Image.open(io.BytesIO(file_bytes))
    
    prompt = """
    You are a GST invoice data extractor.
    Extract all data from this GST invoice image and return ONLY a valid JSON object.
    Do not add any explanation or extra text, just the JSON.
    
    Return this exact structure:
    {
        "seller_name": "",
        "seller_gstin": "",
        "buyer_name": "",
        "buyer_gstin": "",
        "invoice_number": "",
        "invoice_date": "",
        "items": [
            {
                "description": "",
                "quantity": 0,
                "rate": 0,
                "amount": 0
            }
        ],
        "subtotal": 0,
        "cgst": 0,
        "sgst": 0,
        "igst": 0,
        "total": 0
    }
    
    If any field is not found in the invoice, use null for that field.
    """
    
    response = model.generate_content([prompt, image])
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    data = json.loads(text)
    return data