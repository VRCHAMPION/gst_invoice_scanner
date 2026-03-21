import os
import json
import base64
from dotenv import load_dotenv
from groq import Groq
import PIL.Image
import io
import fitz  # PyMuPDF
import docx  # python-docx

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT_TEXT = """You are a GST invoice data extractor.
Extract all data from this GST invoice and return ONLY a valid JSON object.
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

If any field is not found, use null."""

def extract_invoice_data(file_bytes: bytes, content_type: str):
    # Branching logic for different file types
    if content_type == "application/pdf":
        # Convert first page of PDF to image
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        return process_image_bytes(img_bytes)
    
    elif content_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        # Extract text from Word document
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = "\n".join([para.text for para in doc.paragraphs])
        return process_text(full_text)
    
    else:
        # Default as image
        return process_image_bytes(file_bytes)

def process_image_bytes(img_bytes: bytes):
    image = PIL.Image.open(io.BytesIO(img_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    response = client.chat.completions.create(
        model="meta-llama/llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
                    {"type": "text", "text": PROMPT_TEXT}
                ]
            }
        ],
        max_tokens=1500
    )
    return parse_json_response(response.choices[0].message.content)

def process_text(text_content: str):
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are a professional GST invoice parser."},
            {"role": "user", "content": f"{PROMPT_TEXT}\n\nInvoice Text Content:\n{text_content}"}
        ],
        max_tokens=1500
    )
    return parse_json_response(response.choices[0].message.content)

def parse_json_response(text: str):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Fallback if AI output is slightly malformed
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise