# The AI Data Extraction Pipeline 🧠

This document explains exactly how we extract financial data from severely unstructured, blurry, and messy invoices using a hybridized pipeline.

## The Problem with Traditional OCR
Traditional tools (like AWS Textract) require exact bounding-box coordinates for templates. An invoice from Amazon looks entirely different than an invoice from a local Indian hardware store. If the GSTIN is moved 2 inches to the right, a traditional OCR template fails instantly.

## The Hybrid Solution
We built a generalized two-step approach: **A Dumb Reader + A Smart Organizer.**

---

### Step 1: The Dumb Reader (`pytesseract` + `fitz`)
We don't try to identify fields out of the image natively. We just want *words*.
- **PDF Handling:** If a user uploads a PDF, we use `PyMuPDF` (`fitz`) to rapidly render the first 2 pages of the PDF into pixel maps (PNG bytes) entirely in RAM.
- **Image Handling:** We pass these PNG bytes directly into `pytesseract` (Google's open-source Optical Character Recognition engine).
- **The Output:** A massive, chaotic string of text. Line breaks are broken, tables are unaligned, and random serial numbers are floating everywhere.

### Step 2: The Smart Organizer (`Groq llama-3.1-8b-instant`)
We take the chaotic text, purposefully trim it to `text[:3000]` to avoid blowing up the context window (and saving API costs), and pass it to a large language model.

**The Prompt Strategy:**
```text
You are a strict JSON data extractor...
Return ONLY a valid JSON object with EXACTLY these keys:
"seller_gstin" (string or null), "seller_name" (string or null)...
```

Because LLMs inherently "understand" what a GSTIN looks like (e.g. `27AAAAA0000A1Z5`) and what a "Total" amount looks like contextually, it can pluck those values out of the chaotic text string regardless of where they were located physically on the printed page.

### Step 3: The Strict Cleaner
Models sometimes hallucinate markdown formatting (e.g. `` ```json ``). 
To prevent backend parsing crashes, our Python logic strictly searches for the first `{` and the last `}` in the model's response string. 

```python
raw_json = response.choices[0].message.content
start_idx = raw_json.find('{')
end_idx = raw_json.rfind('}')
cleaned_json = raw_json[start_idx:end_idx+1]
data = json.loads(cleaned_json)
```
This guarantees that as long as the model returned a JSON structure anywhere in its message, our backend will successfully ingest the data without throwing a fatal server error.

---

## The Advantages of this Pipeline
1. **Zero Recurring OCR Costs:** By using Tesseract locally instead of Google Cloud Vision API, the initial pixel-to-text conversion is entirely free.
2. **Lightning Fast:** By utilizing Groq's LPU hardware, the LLM parsing step takes less than 500 milliseconds. 
3. **High Tolerance for Noise:** The LLM can logically deduce that "Tota1: $500" actually means "Total: 500", correcting optical errors on the fly.
