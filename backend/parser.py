import os
import io
import json
import time
import structlog
from dotenv import load_dotenv
from groq import Groq

import pytesseract
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageOps

load_dotenv()

_GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not _GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is missing")
_GROQ_API_KEY = _GROQ_API_KEY.strip()

client = Groq(api_key=_GROQ_API_KEY)
log = structlog.get_logger()

# Windows users: uncomment and set tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR accuracy."""
    # Resize large images to save memory (max 2000px width)
    max_width = 2000
    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    gray = gray.filter(ImageFilter.SHARPEN)
    # Binary threshold at 128 works well for most invoices
    gray = gray.point(lambda x: 0 if x < 128 else 255, '1').convert('L')
    return gray


def extract_raw_text(file_bytes: bytes, content_type: str) -> str:
    """Extract text from PDF or image using OCR."""
    text = ""
    try:
        if "pdf" in content_type.lower():
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            # Process first page only to save memory
            for page_num in range(min(1, len(doc))):
                page = doc.load_page(page_num)
                # Reduce DPI to 200 to save memory (was 300)
                mat = fitz.Matrix(200 / 72, 200 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_bytes))
                processed = preprocess_image(image)
                text += pytesseract.image_to_string(processed) + "\n"
                # Clean up to free memory
                del image, processed, pix
            doc.close()
        else:
            image = Image.open(io.BytesIO(file_bytes))
            processed = preprocess_image(image)
            text = pytesseract.image_to_string(processed)
            # Clean up
            del image, processed
        return text
    except fitz.FileDataError as e:
        log.error("ocr_pdf_corrupt", error=str(e))
        return "ERROR_CORRUPT_FILE"
    except Exception as e:
        log.error("ocr_failed", error=str(e))
        return "ERROR_EXTRACTION_FAILURE"


def _call_groq_with_retry(prompt: str, max_attempts: int = 3) -> str:
    """Call Groq API with exponential backoff on rate limit errors."""
    delays = [2, 4, 8]
    
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512,
            )
            log.info("groq_success", attempt=attempt + 1)
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if attempt < max_attempts - 1:
                    wait = delays[attempt]
                    log.warning("groq_retry", attempt=attempt + 1, wait_seconds=wait, error=error_msg[:100])
                    time.sleep(wait)
                else:
                    log.error("groq_exhausted_retries", error=error_msg[:200])
                    raise
            else:
                log.error("groq_api_error", error=error_msg[:200], error_type=type(e).__name__)
                raise


def extract_invoice_data(file_bytes: bytes, content_type: str) -> dict:
    """Extract structured invoice data using OCR + LLM."""
    
    raw_text = extract_raw_text(file_bytes, content_type)

    if raw_text == "ERROR_CORRUPT_FILE":
        return {"status": "failed", "error": "The uploaded PDF is corrupted or encrypted."}
    if raw_text == "ERROR_EXTRACTION_FAILURE" or not raw_text.strip():
        log.warning("ocr_empty_result")
        return {"status": "failed", "error": "Could not extract text from file."}

    # Use Groq LLM to parse OCR text into structured JSON
    # XML tags prevent prompt injection from malicious PDFs
    prompt = f"""You are a JSON data extractor for Indian GST invoices. Extract invoice data from the text inside <raw_text> tags.
Return ONLY valid JSON with these keys (use null if not found):
  "seller_name", "seller_gstin", "buyer_name", "buyer_gstin", 
  "invoice_number", "invoice_date", "subtotal", "cgst", "sgst", "igst", "total"

Example:
Input: "ABC Tech GSTIN 27ABCDE1234F1Z5 Invoice INV-1045 Date 15-10-2024 To XYZ Corp GSTIN 27XYZAB5678C1Z2 Taxable 5000 CGST 450 SGST 450 Total 5900"
Output: {{"seller_name":"ABC Tech","seller_gstin":"27ABCDE1234F1Z5","buyer_name":"XYZ Corp","buyer_gstin":"27XYZAB5678C1Z2","invoice_number":"INV-1045","invoice_date":"15-10-2024","subtotal":5000.0,"cgst":450.0,"sgst":450.0,"igst":null,"total":5900.0}}

<raw_text>
{raw_text[:5000]}
</raw_text>"""

    try:
        raw_json = _call_groq_with_retry(prompt)
        
        start_idx = raw_json.find('{')
        end_idx = raw_json.rfind('}')

        if start_idx == -1 or end_idx == -1:
            log.error("llm_no_json_found", response=raw_json[:200])
            raise ValueError("No JSON object found in response")

        cleaned_json = raw_json[start_idx:end_idx + 1]
        data = json.loads(cleaned_json)
        data["status"] = "completed"

        # Auto-calculate total when LLM failed to extract it
        if not data.get("total") and data.get("subtotal"):
            subtotal = data.get("subtotal") or 0
            cgst    = data.get("cgst") or 0
            sgst    = data.get("sgst") or 0
            igst    = data.get("igst") or 0
            data["total"] = round(subtotal + cgst + sgst + igst, 2)

        return data

    except json.JSONDecodeError as e:
        log.error("llm_json_decode_failed", error=str(e), raw_response=raw_json[:200] if 'raw_json' in locals() else "N/A")
        return {"status": "failed", "error": "Failed to parse OCR text into structured data."}
    except Exception as e:
        log.error("llm_parse_failed", error=str(e), error_type=type(e).__name__)
        return {"status": "failed", "error": "Failed to parse invoice data."}
