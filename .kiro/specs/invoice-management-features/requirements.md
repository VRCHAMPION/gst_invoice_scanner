# Invoice Management Features - Requirements

## Overview
Implement 6 critical production-ready features for the GST Invoice Scanner to improve data quality, user workflow, and business value.

## Features

### 1. Duplicate Invoice Detection
**User Story**: As a user, I want to be prevented from uploading the same invoice twice so that my data stays clean.

**Requirements**:
- Check if `invoice_number` already exists for the company before saving
- If duplicate found, mark invoice as FAILED with error message
- Error message format: "Duplicate invoice: INV-123 was already uploaded on [date] by [user]"
- Show duplicate warning in UI with link to existing invoice

**Acceptance Criteria**:
- Duplicate invoices are rejected during processing
- User sees clear error message with date and uploader info
- Original invoice remains unchanged

### 2. Invoice Status Workflow
**User Story**: As a user, I want to review and approve invoices before they're finalized so I can catch OCR errors.

**Requirements**:
- Add new status field with values: `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `PROCESSING`, `FAILED`
- Default status after successful extraction: `PENDING_REVIEW`
- Add approval/rejection endpoints
- Track who approved/rejected and when
- Add approval workflow to UI

**Acceptance Criteria**:
- Successfully extracted invoices go to PENDING_REVIEW status
- Users can approve or reject invoices
- Audit trail tracks approval actions
- UI shows approval status and actions

### 3. Search & Filters
**User Story**: As a user, I want to search and filter invoices so I can find specific invoices quickly.

**Requirements**:
- Search by: invoice_number, seller_name, buyer_name, seller_gstin, buyer_gstin
- Filter by: date range, amount range, status, vendor
- Combine search + filters
- Pagination works with filters
- Export filtered results

**Acceptance Criteria**:
- Search returns relevant results
- Filters work individually and in combination
- Performance is acceptable with 1000+ invoices
- Export respects active filters

### 4. Vendor Management
**User Story**: As a user, I want to see all my vendors and track spending per vendor.

**Requirements**:
- Auto-create Vendor record from seller_gstin on invoice save
- Vendor model: gstin, name, total_invoices, total_amount
- Vendor list endpoint with analytics
- Vendor detail page showing all invoices
- Update vendor stats when invoices are approved

**Acceptance Criteria**:
- Vendors are automatically created from invoices
- Vendor list shows accurate stats
- Vendor detail shows all related invoices
- Stats update when invoice status changes

### 5. Better Error Recovery
**User Story**: As a user, I want to retry failed invoices or manually enter data when OCR fails.

**Requirements**:
- "Retry" button for FAILED invoices
- Manual data entry form for failed invoices
- Edit extracted data before approval
- Save edited data and mark as manually verified

**Acceptance Criteria**:
- Retry button re-processes the original file
- Manual entry form has all invoice fields
- Edited invoices are marked as manually verified
- Edit history is tracked

### 6. Notifications
**User Story**: As a user, I want email notifications when invoices are processed so I don't have to keep checking.

**Requirements**:
- Email when invoice processing completes (success or failure)
- Daily summary email (optional, user preference)
- Alert on duplicate invoice attempt
- Alert on suspicious invoices (fraud signals)

**Acceptance Criteria**:
- Emails are sent reliably
- Email templates are professional
- Users can opt-in/opt-out of notifications
- Emails contain relevant links to invoices

## Technical Requirements

### Database Changes
- Add `approval_status` field to Invoice model
- Add `approved_by`, `approved_at`, `rejected_by`, `rejected_at` fields
- Add `is_duplicate` boolean field
- Add `manually_verified` boolean field
- Create Vendor model and table
- Add indexes for search performance

### API Changes
- Add approval/rejection endpoints
- Add search/filter endpoint
- Add vendor list/detail endpoints
- Add retry endpoint
- Add manual entry endpoint
- Add edit endpoint

### Frontend Changes
- Add approval UI to results page
- Add search bar and filter panel to history page
- Add vendor list page
- Add vendor detail page
- Add retry button to failed invoices
- Add manual entry form
- Add edit form

### Email Integration
- Set up email service (SendGrid/AWS SES)
- Create email templates
- Add notification preferences to user model
- Implement email queue/background jobs

## Out of Scope
- Mobile app
- Accounting software integration
- GST return generation
- Multi-currency support

## Success Metrics
- Duplicate detection prevents >95% of re-uploads
- Approval workflow catches >80% of OCR errors before finalization
- Search returns results in <500ms
- Email delivery rate >98%
- User satisfaction with new features >4/5
