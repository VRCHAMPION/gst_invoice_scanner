import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

# ── Users Table ───────────────────────────────────────────────────────
def init_users_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def seed_admin_user():
    from auth import hash_password
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        hashed = hash_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, name) VALUES (%s, %s, %s)",
            ("admin", hashed, "Admin User")
        )
        conn.commit()
    cursor.close()
    conn.close()

def create_user(name: str, username: str, password_hash: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, username, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (name, username, password_hash)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, name FROM users WHERE username = %s",
        (username,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "password_hash": row[2], "name": row[3]}
    return None

# ── Invoices ──────────────────────────────────────────────────────────
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

def get_itc_summary():
    conn = get_connection()
    cursor = conn.cursor()

    # Current month ITC
    cursor.execute("""
        SELECT 
            COALESCE(SUM(cgst), 0) as total_cgst,
            COALESCE(SUM(sgst), 0) as total_sgst,
            COALESCE(SUM(igst), 0) as total_igst,
            COALESCE(SUM(cgst + sgst + igst), 0) as total_itc,
            COUNT(*) as invoice_count
        FROM invoices
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
    """)
    current = cursor.fetchone()

    # Previous month ITC
    cursor.execute("""
        SELECT 
            COALESCE(SUM(cgst + sgst + igst), 0) as total_itc
        FROM invoices
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    """)
    previous = cursor.fetchone()

    # Supplier wise ITC breakdown
    cursor.execute("""
        SELECT 
            seller_name,
            seller_gstin,
            COALESCE(SUM(cgst), 0) as cgst,
            COALESCE(SUM(sgst), 0) as sgst,
            COALESCE(SUM(igst), 0) as igst,
            COALESCE(SUM(cgst + sgst + igst), 0) as total_itc
        FROM invoices
        WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY seller_name, seller_gstin
        ORDER BY total_itc DESC
    """)
    suppliers = cursor.fetchall()

    cursor.close()
    conn.close()

    # Calculate percentage change vs last month
    current_itc = float(current[3])
    previous_itc = float(previous[0])

    if previous_itc > 0:
        percentage_change = round(
            ((current_itc - previous_itc) / previous_itc) * 100, 1
        )
    else:
        percentage_change = 0

    return {
        "current_month": {
            "total_cgst": float(current[0]),
            "total_sgst": float(current[1]),
            "total_igst": float(current[2]),
            "total_itc": current_itc,
            "invoice_count": current[4]
        },
        "previous_month_itc": previous_itc,
        "percentage_change": percentage_change,
        "supplier_breakdown": [
            {
                "seller_name": row[0],
                "seller_gstin": row[1],
                "cgst": float(row[2]),
                "sgst": float(row[3]),
                "igst": float(row[4]),
                "total_itc": float(row[5])
            }
            for row in suppliers
        ],
        "disclaimer": "ITC calculated based on invoices scanned in this app only. Ensure all purchase invoices are uploaded for accurate results."
    }