/**
 * @fileoverview Centralized JSDoc type definitions for the GST Invoice Scanner frontend.
 * This file does not emit executable code; it is purely for IDE autocompletion and strict static analysis.
 */

/**
 * @typedef {Object} CurrentUser
 * @property {string} id - The UUID of the user.
 * @property {string} email - The user's email address.
 * @property {string} role - The user's role (e.g., 'owner', 'employee').
 * @property {string} [name] - The optional name of the user.
 * @property {string} [company_id] - The optional UUID of the company they belong to.
 */

/**
 * @typedef {Object} Company
 * @property {string} id - The UUID of the company.
 * @property {string} name - The company's legal name.
 * @property {string} gstin - The 15-character GSTIN.
 * @property {number} [employee_count] - Number of users under this company.
 */

/**
 * @typedef {Object} HealthScore
 * @property {number} score - 0-100 score indicating invoice health.
 * @property {string} grade - Letter grade (A, B, C, F, etc.).
 * @property {string} status - Status code.
 * @property {string[]} issues - List of detected critical issues.
 * @property {string[]} warnings - List of warnings.
 * @property {string[]} passed_checks - List of passed validation checks.
 * @property {string} summary - Human readable summary.
 */

/**
 * @typedef {Object} Invoice
 * @property {string} id - UUID of the invoice record.
 * @property {string} [invoice_number] - The extracted or manually entered invoice number.
 * @property {string} [invoice_date] - The extracted date.
 * @property {number} [total] - The total amount in INR.
 * @property {string} [status] - The current processing/approval status.
 * @property {string} [seller_gstin] - The vendor's GSTIN.
 * @property {string} [seller_name] - Vendor name.
 * @property {HealthScore} [health_score] - Computed health score metrics.
 */

/**
 * @typedef {Object} Vendor 
 * @property {string} id - UUID of the vendor.
 * @property {string} gstin - The vendor's GSTIN.
 * @property {string} name - Legal name of the vendor.
 * @property {number} total_invoices - Total number of approved invoices.
 * @property {number} total_amount - Total value accumulated across approved invoices.
 * @property {number} [trust_score] - 0-100 metric tracking vendor reliability.
 * @property {string} [trust_label] - Human readable trust tier designation.
 */
