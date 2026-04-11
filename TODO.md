# TODO

## High Priority
- [ ] Add batch upload support (multiple files at once)
- [ ] Better error messages when OCR fails
- [ ] Fix mobile layout issues on small screens

## Medium Priority
- [ ] Migrate to Celery for background jobs (when we hit scale)
- [ ] Add invoice line items table (currently just storing totals)
- [ ] Implement GSTIN checksum validation
- [ ] Add export to Excel (not just CSV)

## Low Priority
- [ ] Dark mode toggle
- [ ] Email notifications for completed scans
- [ ] Invoice templates/favorites

## Bugs
- [ ] Drag-drop doesn't work on mobile Safari
- [ ] Polling sometimes doesn't stop on network errors
- [ ] Remember me checkbox doesn't persist on some browsers

## Ideas
- Maybe add confidence scores from OCR?
- Fraud detection using ML?
- Support for other document types (receipts, bills)?
