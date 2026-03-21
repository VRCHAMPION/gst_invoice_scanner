import os
import json
import base64
from dotenv import load_dotenv
from groq import Groq
import PIL.Image
import io

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_invoice_data(file_bytes: bytes, content_type: str):

    # Convert image to base64
    image = PIL.Image.open(io.BytesIO(file_bytes))
    
    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """You are a GST invoice data extractor.
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

If any field is not found in the invoice, use null for that field."""
                    }
                ]
            }
        ],
        max_tokens=1500
    )

    text = response.choices[0].message.content.strip()

    # Clean markdown if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()
    data = json.loads(text)
    return data