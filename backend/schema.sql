-- GST Invoice Scanner - PostgreSQL/Neon Schema (UUID-based RBAC)

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Companies Table
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    gstin VARCHAR(15) UNIQUE NOT NULL,
    owner_id UUID, -- Circular reference handled after users table
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 2. Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'employee')),
    company_id UUID REFERENCES companies(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Add circular FK for owner recognition
ALTER TABLE companies ADD CONSTRAINT fk_company_owner FOREIGN KEY (owner_id) REFERENCES users(id);

-- 3. Invoices Table
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    
    invoice_number VARCHAR(100),
    invoice_date VARCHAR(100),
    seller_name VARCHAR(255),
    seller_gstin VARCHAR(15),
    buyer_name VARCHAR(255),
    buyer_gstin VARCHAR(15),
    
    subtotal FLOAT DEFAULT 0,
    cgst FLOAT DEFAULT 0,
    sgst FLOAT DEFAULT 0,
    igst FLOAT DEFAULT 0,
    total FLOAT DEFAULT 0,
    
    status VARCHAR(50) DEFAULT 'PROCESSING',
    error_message TEXT,
    
    raw_json JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- Indices for performance
CREATE INDEX idx_user_company ON users(company_id);
CREATE INDEX idx_invoice_company ON invoices(company_id);
CREATE INDEX idx_invoice_user ON invoices(uploaded_by);
