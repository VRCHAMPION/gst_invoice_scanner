import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

def save_invoice(data):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO invoices (
            seller_name, seller_gstin, buyer_name, buyer_gstin,
            invoice_number, invoice_date, cgst, sgst, igst,
            subtotal, total, items
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        data.get("seller_name"),
        data.get("seller_gstin"),
        data.get("buyer_name"),
        data.get("buyer_gstin"),
        data.get("invoice_number"),
        data.get("invoice_date"),
        data.get("cgst"),
        data.get("sgst"),
        data.get("igst"),
        data.get("subtotal"),
        data.get("total"),
        json.dumps(data.get("items"))
    ))
    
    invoice_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return invoice_id

def get_all_invoices():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, seller_name, buyer_name, invoice_number, 
               invoice_date, total, created_at 
        FROM invoices 
        ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_analytics():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_invoices,
            COALESCE(SUM(total), 0) as total_spend,
            COALESCE(SUM(cgst + sgst + igst), 0) as total_tax
        FROM invoices
    """)
    summary = cursor.fetchone()

    cursor.execute("""
        SELECT 
            seller_name,
            seller_gstin,
            SUM(total) as total_spend,
            COUNT(*) as invoice_count
        FROM invoices
        GROUP BY seller_name, seller_gstin
        ORDER BY total_spend DESC
        LIMIT 5
    """)
    top_suppliers = cursor.fetchall()

    cursor.execute("""
        SELECT 
            TO_CHAR(created_at, 'Mon YYYY') as month,
            SUM(total) as total,
            SUM(cgst + sgst + igst) as tax
        FROM invoices
        GROUP BY TO_CHAR(created_at, 'Mon YYYY'), 
                 DATE_TRUNC('month', created_at)
        ORDER BY DATE_TRUNC('month', created_at)
    """)
    monthly_spend = cursor.fetchall()

    cursor.execute("""
        SELECT 
            TO_CHAR(created_at, 'Mon YYYY') as month,
            COUNT(*) as count
        FROM invoices
        GROUP BY TO_CHAR(created_at, 'Mon YYYY'),
                 DATE_TRUNC('month', created_at)
        ORDER BY DATE_TRUNC('month', created_at)
    """)
    monthly_count = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "total_invoices": summary[0],
        "total_spend": float(summary[1]),
        "total_tax": float(summary[2]),
        "top_suppliers": [
            {
                "name": row[0],
                "gstin": row[1],
                "total_spend": float(row[2]),
                "invoice_count": row[3]
            }
            for row in top_suppliers
        ],
        "monthly_spend": [
            {
                "month": row[0],
                "total": float(row[1]),
                "tax": float(row[2])
            }
            for row in monthly_spend
        ],
        "monthly_invoice_count": [
            {
                "month": row[0],
                "count": row[1]
            }
            for row in monthly_count
        ]
    }