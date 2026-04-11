# Invoice Management Features - Tasks

## Phase 1: Backend Core Features

### 1. Database Schema Updates
- [x] 1.1 Update Invoice model in models.py with new fields
- [x] 1.2 Add Vendor model to models.py
- [x] 1.3 Create database migration script
- [x] 1.4 Test migration on local database

### 2. Duplicate Detection
- [x] 2.1 Add duplicate check logic to invoice_service.py
- [x] 2.2 Query existing invoices by invoice_number + company_id
- [x] 2.3 Mark duplicates as FAILED with descriptive error
- [x] 2.4 Test duplicate detection with sample invoices

### 3. Approval Workflow Backend
- [x] 3.1 Add approve endpoint to invoices router
- [x] 3.2 Add reject endpoint to invoices router
- [x] 3.3 Update invoice status to PENDING_REVIEW after extraction
- [x] 3.4 Add approval validation (only PENDING_REVIEW can be approved)
- [x] 3.5 Test approval/rejection flow

### 4. Search & Filter Backend
- [x] 4.1 Add search endpoint with query parameter
- [x] 4.2 Implement text search on invoice_number, seller_name, buyer_name
- [x] 4.3 Add status filter
- [x] 4.4 Add date range filter
- [x] 4.5 Add amount range filter
- [x] 4.6 Add vendor (seller_gstin) filter
- [x] 4.7 Combine filters with AND logic
- [x] 4.8 Test search with various combinations

### 5. Vendor Management Backend
- [x] 5.1 Add vendor auto-creation logic in invoice_service.py
- [x] 5.2 Create or update vendor on invoice approval
- [x] 5.3 Add vendor list endpoint
- [x] 5.4 Add vendor detail endpoint
- [x] 5.5 Add vendor invoices endpoint
- [x] 5.6 Test vendor creation and stats updates

## Phase 2: Frontend Core Features

### 6. Approval Workflow UI
- [x] 6.1 Add approval status badge to results page
- [x] 6.2 Add Approve button to results page
- [x] 6.3 Add Reject button to results page
- [x] 6.4 Show approval confirmation modal
- [x] 6.5 Update UI after approval/rejection
- [x] 6.6 Test approval workflow in UI

### 7. Search & Filter UI
- [x] 7.1 Add search bar to history page
- [x] 7.2 Add filter panel with status dropdown
- [x] 7.3 Add date range picker
- [x] 7.4 Add amount range inputs
- [x] 7.5 Add vendor dropdown
- [x] 7.6 Wire up search/filter to API
- [x] 7.7 Update results on filter change
- [x] 7.8 Test search and filters in UI

### 8. Duplicate Warning UI
- [ ] 8.1 Show duplicate warning on results page
- [ ] 8.2 Add link to original invoice
- [ ] 8.3 Style duplicate warning prominently
- [ ] 8.4 Test duplicate warning display

### 9. Vendor Management UI
- [x] 9.1 Create vendors list page
- [x] 9.2 Add vendor card with stats
- [x] 9.3 Create vendor detail page
- [x] 9.4 Show vendor invoices list
- [x] 9.5 Add navigation to vendors page
- [x] 9.6 Test vendor pages

## Phase 3: Error Recovery Features

### 10. Retry Failed Invoices
- [ ] 10.1 Add retry endpoint to invoices router
- [ ] 10.2 Fetch original file from storage (if available)
- [ ] 10.3 Re-process invoice with same file
- [ ] 10.4 Add Retry button to failed invoice UI
- [ ] 10.5 Test retry functionality

### 11. Manual Data Entry
- [ ] 11.1 Create manual entry form component
- [ ] 11.2 Add all invoice fields to form
- [ ] 11.3 Add manual entry endpoint
- [ ] 11.4 Mark manually entered invoices
- [ ] 11.5 Add manual entry button to failed invoices
- [ ] 11.6 Test manual entry flow

### 12. Edit Invoice Data
- [ ] 12.1 Create edit form component
- [ ] 12.2 Pre-fill form with existing data
- [ ] 12.3 Add update endpoint
- [ ] 12.4 Track edit history in raw_json
- [ ] 12.5 Add Edit button to invoice detail
- [ ] 12.6 Test edit functionality

## Phase 4: Notifications (Optional)

### 13. Email Service Setup
- [ ] 13.1 Choose email service (SendGrid/AWS SES)
- [ ] 13.2 Set up email service account
- [ ] 13.3 Add email credentials to environment
- [ ] 13.4 Install email library
- [ ] 13.5 Test email sending

### 14. Email Templates
- [ ] 14.1 Create invoice processed email template
- [ ] 14.2 Create duplicate alert email template
- [ ] 14.3 Create daily summary email template
- [ ] 14.4 Style email templates
- [ ] 14.5 Test email templates

### 15. Notification Logic
- [ ] 15.1 Add email notification to invoice_service.py
- [ ] 15.2 Send email on invoice success
- [ ] 15.3 Send email on invoice failure
- [ ] 15.4 Send email on duplicate detection
- [ ] 15.5 Add notification preferences to user model
- [ ] 15.6 Respect user notification preferences
- [ ] 15.7 Test notification sending

## Testing & Deployment

### 16. Testing
- [ ] 16.1 Write unit tests for duplicate detection
- [ ] 16.2 Write unit tests for approval workflow
- [ ] 16.3 Write integration tests for search/filter
- [ ] 16.4 Write E2E tests for full workflows
- [ ] 16.5 Test with 1000+ invoices for performance

### 17. Deployment
- [ ] 17.1 Run database migrations on production
- [ ] 17.2 Deploy backend changes
- [ ] 17.3 Deploy frontend changes
- [ ] 17.4 Monitor logs for errors
- [ ] 17.5 Verify all features work in production

## Documentation

### 18. Documentation
- [ ] 18.1 Update API documentation
- [ ] 18.2 Create user guide for new features
- [ ] 18.3 Document approval workflow
- [ ] 18.4 Document search/filter usage
- [ ] 18.5 Document vendor management
