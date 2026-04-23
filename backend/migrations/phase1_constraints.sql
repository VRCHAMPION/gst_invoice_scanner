-- ============================================================
-- Phase 1 Migration: Database-Level Constraints
-- GST Invoice Scanner — Enterprise Upgrade
--
-- Run this in: Supabase Dashboard → SQL Editor
-- IMPORTANT: Run each block one at a time and verify before
-- proceeding. Constraints will FAIL if existing data violates them.
-- Clean bad data first using the diagnostic queries below.
-- ============================================================


-- ── STEP 0: Diagnostic — check for data that will violate new constraints ────

-- Check for invalid GSTINs in companies
SELECT id, name, gstin FROM companies
WHERE gstin !~ '^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$';

-- Check for invalid GSTINs in vendors
SELECT id, name, gstin FROM vendors
WHERE gstin !~ '^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$';

-- Check for invalid invoice statuses
SELECT id, status FROM invoices
WHERE status NOT IN ('PROCESSING','PENDING_REVIEW','APPROVED','REJECTED','FAILED');

-- Check for invalid approval statuses
SELECT id, approval_status FROM invoices
WHERE approval_status IS NOT NULL
  AND approval_status NOT IN ('approved','rejected');

-- Check for negative totals
SELECT id, total FROM invoices WHERE total < 0;

-- Check for invalid join request statuses
SELECT id, status FROM join_requests
WHERE status NOT IN ('pending','accepted','rejected');


-- ── STEP 1: users table constraints ─────────────────────────────────────────

ALTER TABLE users
    ADD CONSTRAINT ck_users_role
    CHECK (role IN ('owner', 'employee'));

ALTER TABLE users
    ADD CONSTRAINT ck_users_email_format
    CHECK (email ~ '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$');


-- ── STEP 2: companies table constraints ──────────────────────────────────────

ALTER TABLE companies
    ADD CONSTRAINT ck_companies_gstin_format
    CHECK (gstin ~ '^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$');


-- ── STEP 3: invoices table constraints ───────────────────────────────────────

ALTER TABLE invoices
    ADD CONSTRAINT ck_invoice_status
    CHECK (status IN ('PROCESSING','PENDING_REVIEW','APPROVED','REJECTED','FAILED'));

ALTER TABLE invoices
    ADD CONSTRAINT ck_invoice_approval_status
    CHECK (approval_status IS NULL OR approval_status IN ('approved','rejected'));

ALTER TABLE invoices
    ADD CONSTRAINT ck_invoice_total_non_negative
    CHECK (total IS NULL OR total >= 0);


-- ── STEP 4: join_requests table constraints ───────────────────────────────────

ALTER TABLE join_requests
    ADD CONSTRAINT ck_join_request_status
    CHECK (status IN ('pending','accepted','rejected'));


-- ── STEP 5: vendors table constraints ────────────────────────────────────────

ALTER TABLE vendors
    ADD CONSTRAINT ck_vendors_gstin_format
    CHECK (gstin ~ '^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$');


-- ── Verify all constraints were applied ──────────────────────────────────────

SELECT conname, contype, conrelid::regclass AS table_name
FROM pg_constraint
WHERE conname LIKE 'ck_%'
ORDER BY conrelid::regclass::text, conname;
