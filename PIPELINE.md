
# 🔄 PIPELINE.md — GST Invoice Scanner

## 1. Pipeline Overview

The GST Invoice Scanner pipeline converts raw invoice files into structured tax data through a staged OCR workflow. A file is first validated, converted into page images if needed, cleaned for OCR, passed through OCR, post-processed, parsed into GST-specific fields, validated for consistency, and finally exported as JSON/CSV/Excel.

```mermaid
flowchart LR
    A[Input] --> B[Validation]
    B --> C[Preprocessing]
    C --> D[OCR]
    D --> E[Text Cleaning]
    E --> F[Field Extraction]
    F --> G[Validation]
    G --> H[Formatting]
    H --> I[Output]
```

---

## 2. Stage 1: Input Ingestion

### Purpose
Accept invoice files and ensure they are valid before processing.

### Supported Formats
- PDF
- JPG
- PNG
- TIFF

### Input Modes
- **Single file mode** — one invoice at a time
- **Batch mode** — process all supported files in a folder

### Processing
- Detect MIME type / extension
- Validate file size and supported format
- For PDF:
  - split into pages
  - render each page as an image
- For images:
  - load directly into memory

### Input / Output
- **Input:** raw file
- **Output:** validated file object / page images

---

## 3. Stage 2: Image Preprocessing

### Purpose
Improve OCR quality before text extraction.

### Steps
1. **PDF to image conversion** at **300 DPI**
2. **Grayscale conversion**
3. **Noise reduction**
   - Gaussian blur
   - Median filter
4. **Contrast enhancement**
   - CLAHE / histogram equalization
5. **Binarization**
   - Otsu threshold
   - Adaptive threshold
6. **Deskew / rotation correction**
7. **Border removal / cropping**

### Libraries
- OpenCV
- Pillow
- NumPy

### Input / Output
- **Input:** raw image
- **Output:** cleaned binary image

### Before / After
- **Before:** colored, noisy, rotated invoice scan
- **After:** sharp, high-contrast, aligned black-and-white image

---

## 4. Stage 3: OCR (Optical Character Recognition)

### Purpose
Convert cleaned invoice images into raw text.

### Engine
- **Primary:** Tesseract OCR
- **Fallback:** EasyOCR
- **Last resort:** manual review / error flag

### Configuration
- Language packs:
  - `eng`
  - `hin` (if bilingual invoices are supported)
- PSM logic:
  - `--psm 6` for structured blocks
  - `--psm 11` for sparse text
- Confidence threshold:
  - low-confidence pages can be retried with fallback OCR

### Input / Output
- **Input:** preprocessed image
- **Output:** raw OCR text + confidence scores

### Benchmark Targets
- Avg processing time: **1–3 sec/page**
- OCR accuracy target: **85–95%** depending on scan quality

---

## 5. Stage 4: Text Post-Processing

### Purpose
Clean OCR output so extraction rules work more reliably.

### Steps
- Remove non-printable characters
- Fix common OCR mistakes:
  - `0 ↔ O`
  - `1 ↔ I ↔ l`
  - `S ↔ 5`
- Normalize spaces and line breaks
- Group related lines into blocks
- Detect common sections:
  - Seller details
  - Buyer details
  - Tax summary
  - Item table

### Input / Output
- **Input:** raw OCR text
- **Output:** cleaned structured text blocks

---

## 6. Stage 5: Field Extraction

### Purpose
Extract GST-specific invoice fields from cleaned text.

| Field | Method | Regex / Logic |
|---|---|---|
| GSTIN (Seller) | Regex | `[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}` |
| GSTIN (Buyer) | Regex + Context | Search near `Bill To`, `Buyer`, `Ship To` |
| Invoice Number | Regex + KV pair | Match keys like `Invoice No`, `Inv No` |
| Invoice Date | Regex | `DD/MM/YYYY`, `DD-MM-YYYY` |
| Taxable Amount | Regex + Context | Value near `Taxable Amount` |
| CGST / SGST / IGST | Regex + Table | Parse rate and amount lines |
| Total Amount | Regex | Near `Grand Total`, `Total Amount` |
| HSN/SAC Code | Regex | 4–8 digit numeric code |
| Line Items | Table parsing | Row-wise extraction from item section |

### Confidence Scoring
Each extracted field can be tagged with:
- OCR confidence
- regex / parser confidence
- validation status

### Input / Output
- **Input:** cleaned text
- **Output:** extracted dictionary / key-value pairs

---

## 7. Stage 6: Validation & Cross-Verification

### Purpose
Check whether extracted fields are structurally and logically valid.

### Validation Rules
- **GSTIN**
  - pattern match
  - checksum validation
- **Date**
  - valid calendar date
- **Tax arithmetic**
  - taxable amount × rate ≈ tax amount
  - CGST + SGST or IGST consistency
- **Mandatory fields**
  - invoice number
  - date
  - seller GSTIN
  - total amount

### Output
- validated fields
- validation report with pass/fail per field

### Input / Output
- **Input:** extracted fields
- **Output:** validated fields + report

---

## 8. Stage 7: Output Generation

### Purpose
Format final extracted data for downstream use.

### Output Types
- **JSON**
- **CSV**
- **Excel**
- **Database record** (if persistence is enabled)

### Example JSON
```json
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

### Input / Output
- **Input:** validated fields
- **Output:** JSON / CSV / Excel file

---

## 9. Error Handling at Each Stage

| Stage | Possible Errors | Handling Strategy | Fallback |
|---|---|---|---|
| Input | Unsupported file type | Reject request | User re-upload |
| Validation | Corrupt PDF / image | Mark failed | Skip file |
| Preprocessing | OpenCV conversion error | Log and continue with original image | Raw OCR |
| OCR | Low confidence / OCR failure | Retry with different PSM | EasyOCR |
| Text Cleaning | Broken text blocks | Apply generic normalization | Partial extraction |
| Field Extraction | Missing fields | Context-based search retry | Null + warning |
| Validation | Tax mismatch | Mark as inconsistent | Export with validation flag |
| Output | File export issue | Retry save / stream response | JSON only |

---

## 10. Pipeline Configuration

### Configurable Parameters
- supported file types
- max file size
- PDF render DPI
- OCR engine
- OCR language
- confidence threshold
- output format
- batch size

### Example Config (`config.yaml`)
```yaml
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

## 11. Performance Metrics

| Metric | Typical Range |
|---|---|
| Avg processing time per invoice | 2–8 sec |
| Avg processing time per page | 1–3 sec |
| OCR accuracy | 85–95% |
| Field extraction accuracy | 80–92% |
| Throughput | 10–30 invoices/min |

> Actual performance depends on invoice quality, page count, and OCR engine configuration.

---

## 12. Pipeline Execution Modes

### Single Invoice
Used for CLI-based one-off extraction.

```bash
python main.py --input invoice.pdf --output result.json
```

### Batch Processing
Process all invoices in a directory.

```bash
python main.py --input ./invoices/ --output ./results/ --format csv
```

### API-Triggered
Real-time upload via backend API.

```bash
curl -X POST http://localhost:8000/extract -F "file=@invoice.pdf"
```

### Scheduled Processing
Can be triggered periodically using cron / scheduler for inbox folders.

```bash
0 * * * * python batch_runner.py
```

---

## Summary

The pipeline is designed as a clear staged workflow:
1. ingest file
2. validate format
3. preprocess image
4. run OCR
5. clean text
6. extract GST fields
7. validate values
8. export structured output

This staged structure makes the system easy to debug, improve, and extend.
