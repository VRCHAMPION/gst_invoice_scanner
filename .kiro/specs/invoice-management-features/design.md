# Invoice Management Features - Design

## Architecture Overview

This feature set adds production-ready invoice management capabilities including duplicate detection, approval workflows, search/filtering, vendor management, error recovery, and notifications.

## Database Schema Changes

### Invoice Table Modifications
```sql
ALTER TABLE invoices ADD COLUMN approval_status VARCHAR;
ALTER TABLE invoices ADD COLUMN approved_by UUID REFERENCES users(id);
ALTER TABLE invoices ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE invoices ADD COLUMN is_duplicate VARCHAR;
ALTER TABLE invoices ADD COLUMN manually_verified VARCHAR;
ALTER TABLE invoices ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

CREATE INDEX ix_invoices_company_invoice_number ON invoices(company_id, invoice_number);
CREATE INDEX ix_invoices_seller_gstin ON invoices(seller_gstin);
```

### New Vendor Table
```sql
CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id),
    gstin VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    total_invoices INTEGER DEFAULT 0,
    total_amount FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_vendors_company_gstin ON vendors(company_id, gstin);
```

## API Endpoints

### Duplicate Detection
- Implemented in `process_invoice_background()` service
- Check before saving: `SELECT id, created_at, uploaded_by FROM invoices WHERE company_id = ? AND invoice_number = ? AND status != 'FAILED'`
- If found, mark as FAILED with duplicate error

### Approval Workflow
```
POST /api/invoices/{invoice_id}/approve
POST /api/invoices/{invoice_id}/reject
GET /api/invoices?status=PENDING_REVIEW
```

### Search & Filters
```
GET /api/invoices/search?q={query}&status={status}&date_from={date}&date_to={date}&vendor={gstin}&amount_min={min}&amount_max={max}
```

### Vendor Management
```
GET /api/vendors
GET /api/vendors/{vendor_id}
GET /api/vendors/{vendor_id}/invoices
```

### Error Recovery
```
POST /api/invoices/{invoice_id}/retry
POST /api/invoices/manual
PUT /api/invoices/{invoice_id}
```

## Implementation Plan

### Phase 1: Backend Core (Priority 1)
1. Update models.py with new fields
2. Implement duplicate detection in invoice_service.py
3. Add approval endpoints to invoices router
4. Add search/filter logic to invoices router
5. Implement vendor auto-creation logic

### Phase 2: Frontend Core (Priority 1)
1. Add approval buttons to results page
2. Add search bar to history page
3. Add filter panel to history page
4. Show duplicate warnings
5. Add vendor list page

### Phase 3: Error Recovery (Priority 2)
1. Add retry endpoint
2. Add manual entry form
3. Add edit form
4. Update UI to show retry/edit options

### Phase 4: Notifications (Priority 3)
1. Set up email service integration
2. Create email templates
3. Add notification preferences to user model
4. Implement email sending logic
5. Add email queue for reliability

## Technical Decisions

### Duplicate Detection Strategy
- Check on `invoice_number` + `company_id` combination
- Ignore FAILED invoices in duplicate check
- Store original invoice ID in `is_duplicate` field for reference

### Approval Workflow
- Default status after extraction: `PENDING_REVIEW`
- Only APPROVED invoices count in analytics
- Rejected invoices are kept for audit trail

### Search Implementation
- Use PostgreSQL full-text search for text fields
- Use indexes for GSTIN and invoice_number lookups
- Combine filters with AND logic
- Pagination with LIMIT/OFFSET

### Vendor Management
- Auto-create vendor on first invoice with that seller_gstin
- Update vendor stats only for APPROVED invoices
- Vendor stats recalculated on approval/rejection

## Security Considerations
- All endpoints require authentication
- Users can only access their company's data
- Approval actions are logged with user ID and timestamp
- Edit history is tracked in raw_json

## Performance Considerations
- Add database indexes for search fields
- Limit search results to 1000 max
- Cache vendor stats (update on approval only)
- Use background jobs for email sending

## Testing Strategy
- Unit tests for duplicate detection logic
- Integration tests for approval workflow
- E2E tests for search/filter combinations
- Load testing with 10,000+ invoices

## Rollout Plan
1. Deploy database migrations
2. Deploy backend changes
3. Deploy frontend changes
4. Monitor for errors
5. Gradual rollout of email notifications
