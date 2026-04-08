# Pipeline — GST Invoice Scanner

## Overview

This pipeline converts raw invoice files into structured GST data through a series of clearly defined stages.

Each stage has a specific responsibility, making the system easier to debug, improve, and scale.

The overall flow:

* Ingest file
* Validate input
* Preprocess image
* Extract text (OCR)
* Clean text
* Extract GST fields
* Validate results
* Export structured output

---

## 1. Input Ingestion

### Purpose

Accept invoice files and ensure they are valid before processing.

### Supported Formats

* PDF
* JPG
* PNG
* TIFF

### Input Modes

* Single file processing
* Batch processing (folder input)

### Processing Steps

* Detect file type
* Validate format and file size
* For PDFs:

  * Split into pages
  * Convert each page to an image
* For images:

  * Load directly into memory

### Output

Validated file or list of page images

---

## 2. Image Preprocessing

### Purpose

Improve image quality to increase OCR accuracy.

### Steps

* Convert to grayscale
* Reduce noise (Gaussian / median filters)
* Enhance contrast (CLAHE / histogram equalization)
* Apply binarization (Otsu / adaptive thresholding)
* Correct skew and rotation
* Remove borders and crop

### Libraries

* OpenCV
* Pillow
* NumPy

### Output

Clean, high-contrast image optimized for OCR

---

## 3. OCR (Optical Character Recognition)

### Purpose

Convert images into raw text.

### Engines

* Primary: Tesseract
* Fallback: EasyOCR
* Last resort: manual review / error flag

### Configuration

* Language: English (optional Hindi support)
* Page segmentation modes:

  * Structured text: `--psm 6`
  * Sparse text: `--psm 11`
* Retry logic for low-confidence outputs

### Output

* Raw extracted text
* Confidence scores

### Expected Performance

* 1–3 seconds per page
* 85–95% accuracy depending on scan quality

---

## 4. Text Post-Processing

### Purpose

Clean and normalize OCR output before extraction.

### Steps

* Remove non-printable characters
* Correct common OCR errors:

  * 0 ↔ O
  * 1 ↔ I / l
  * 5 ↔ S
* Normalize spacing and line breaks
* Group text into logical sections:

  * Seller details
  * Buyer details
  * Tax summary
  * Item table

### Output

Structured text blocks

---

## 5. Field Extraction

### Purpose

Extract GST-specific data from cleaned text.

### Key Fields

* Seller GSTIN
* Buyer GSTIN
* Invoice number
* Invoice date
* Taxable amount
* CGST / SGST / IGST
* Total amount
* HSN/SAC codes
* Line items

### Extraction Methods

* Regex patterns
* Context-based matching
* Table parsing for item rows

### Confidence Scoring

Each field can include:

* OCR confidence
* Parsing confidence
* Validation status

### Output

Structured key-value data

---

## 6. Validation and Cross-Verification

### Purpose

Ensure extracted data is logically and structurally correct.

### Validation Rules

* GSTIN format and checksum
* Valid date formats
* Tax calculations:

  * Taxable amount × rate ≈ tax
* Consistency:

  * CGST + SGST vs IGST
* Mandatory fields:

  * Invoice number
  * Date
  * Seller GSTIN
  * Total amount

### Output

* Validated data
* Field-level validation report

---

## 7. Output Generation

### Purpose

Prepare structured data for downstream use.

### Output Formats

* JSON
* CSV
* Excel
* Database records

### Example

```json id="y1k9l2"
{
  "invoice_number": "INV-1024",
  "invoice_date": "12-06-2025",
  "seller_gstin": "29ABCDE1234F1Z5",
  "buyer_gstin": "27PQRSX5678L1Z2",
  "taxable_amount": 10000.0,
  "cgst": 900.0,
  "sgst": 900.0,
  "igst": 0.0,
  "total_amount": 11800.0,
  "confidence": {
    "invoice_number": 0.96,
    "seller_gstin": 0.93
  }
}
```

---

## 8. Error Handling

Each stage includes fallback mechanisms to improve robustness.

| Stage         | Issue                  | Handling Strategy             | Fallback       |
| ------------- | ---------------------- | ----------------------------- | -------------- |
| Input         | Unsupported file       | Reject request                | User re-upload |
| Validation    | Corrupt file           | Intercept fitz.FileDataError | DB: FAILED     |
| Preprocessing | Image conversion error | Use original image            | Raw OCR        |
| OCR           | Low confidence         | Send raw anyway to LLM        | LLM deciphers  |
| Text Cleaning | Prompt Injection       | XML boundary wrappers         | Ignore payload |
| Extraction    | Missing fields         | Strict JSON generation schema | Null values    |
| Validation    | Tax mismatch           | Flag inconsistency            | UI Warning flag|

---

## 9. Configuration

The pipeline is configurable via a YAML file.

### Example

```yaml id="6l9x2p"
input:
  formats: [pdf, jpg, png, tiff]
  max_file_size_mb: 20

preprocessing:
  dpi: 300
  grayscale: true
  denoise: true
  threshold: otsu
  deskew: true

ocr:
  engine: tesseract
  language: eng
  fallback_engine: easyocr
  confidence_threshold: 0.60
  psm: 6

output:
  format: json
  save_validation_report: true
```

---

## 10. Performance Metrics

| Metric                        | Typical Range      |
| ----------------------------- | ------------------ |
| Processing time (per invoice) | 2–8 seconds        |
| Processing time (per page)    | 1–3 seconds        |
| OCR accuracy                  | 85–95%             |
| Field extraction accuracy     | 80–92%             |
| Throughput                    | 10–30 invoices/min |

Performance depends on invoice quality and system configuration.

---

## 11. Execution Modes

### Single File

```bash id="8y2q1z"
python main.py --input invoice.pdf --output result.json
```

### Batch Processing

```bash id="m3x7c1"
python main.py --input ./invoices/ --output ./results/ --format csv
```

### API Mode

```bash id="r4n8k2"
curl -X POST http://localhost:8000/extract -F "file=@invoice.pdf"
```

### Scheduled Processing

```bash id="q2t9p0"
0 * * * * python batch_runner.py
```

---

## Summary

The pipeline is designed as a modular, stage-based workflow that separates concerns clearly.

This makes it:

* Easier to debug
* Easier to extend
* Suitable for scaling into production systems
