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