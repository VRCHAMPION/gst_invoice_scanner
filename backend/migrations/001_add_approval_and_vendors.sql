-- Description: Adds approval status fields to invoices, creates vendors table

-- Add new columns to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approval_status VARCHAR;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS is_duplicate VARCHAR;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS manually_verified VARCHAR;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Add indexes for better search performance
CREATE INDEX IF NOT EXISTS ix_invoices_company_invoice_number ON invoices(company_id, invoice_number);
CREATE INDEX IF NOT EXISTS ix_invoices_seller_gstin ON invoices(seller_gstin);
CREATE INDEX IF NOT EXISTS ix_invoices_seller_name ON invoices(seller_name);
CREATE INDEX IF NOT EXISTS ix_invoices_invoice_number ON invoices(invoice_number);

-- Create vendors table
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    gstin VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    total_invoices INTEGER DEFAULT 0,
    total_amount DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add unique constraint for company + gstin
CREATE UNIQUE INDEX IF NOT EXISTS ix_vendors_company_gstin ON vendors(company_id, gstin);

-- Update existing SUCCESS invoices to PENDING_REVIEW (optional - comment out if you want to keep existing as-is)
-- UPDATE invoices SET status = 'PENDING_REVIEW' WHERE status = 'SUCCESS';

-- Backfill vendors from existing invoices (optional)
-- INSERT INTO vendors (company_id, gstin, name, total_invoices, total_amount)
-- SELECT 
--     company_id,
--     seller_gstin,
--     seller_name,
--     COUNT(*) as total_invoices,
--     SUM(total) as total_amount
-- FROM invoices
-- WHERE seller_gstin IS NOT NULL 
--   AND seller_name IS NOT NULL
--   AND status = 'SUCCESS'
-- GROUP BY company_id, seller_gstin, seller_name
-- ON CONFLICT (company_id, gstin) DO NOTHING;
