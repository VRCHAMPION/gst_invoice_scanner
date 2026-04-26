import os
import requests
from dotenv import load_dotenv
import sys

# Fix encoding issue for Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('backend/.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
API_BASE = 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com/api'

COMPANIES = [
    {"email": "owner1@gmail.com", "name": "Owner 1", "company": "TechCorp India", "gstin": "27AADCB2230M1Z2"},
    {"email": "owner2@gmail.com", "name": "Owner 2", "company": "Global Solutions", "gstin": "29ABCDE1234F2Z5"},
    {"email": "owner3@gmail.com", "name": "Owner 3", "company": "Innovatex Pvt Ltd", "gstin": "07AACCI1234G1Z2"},
    {"email": "owner4@gmail.com", "name": "Owner 4", "company": "Smart Systems", "gstin": "33AABCS1429B1Z4"},
    {"email": "owner5@gmail.com", "name": "Owner 5", "company": "NextGen Tech", "gstin": "19AAAAA0000A1Z5"}
]

PASSWORD = "Owner@123"

def register_and_onboard():
    for c in COMPANIES:
        print(f"Registering {c['email']}...")
        
        # 1. Sign Up to Supabase
        signup_url = f"{SUPABASE_URL}/auth/v1/signup"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "email": c["email"],
            "password": PASSWORD,
            "data": {
                "full_name": c["name"]
            }
        }
        res = requests.post(signup_url, headers=headers, json=payload)
        
        if res.status_code not in [200, 201]:
            print(f"Failed to sign up {c['email']}: {res.text}")
            continue
            
        data = res.json()
        access_token = data.get("access_token")
        
        if not access_token:
            print(f"No access token for {c['email']} (User might already exist)")
            # Try to log in to get the token instead
            login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            login_res = requests.post(login_url, headers=headers, json={"email": c["email"], "password": PASSWORD})
            if login_res.status_code == 200:
                access_token = login_res.json().get("access_token")
                print("Successfully logged into existing account.")
            else:
                print(f"Failed to login: {login_res.text}")
                continue
            
        print(f"Successfully got access token. Establishing backend session...")
        
        # 2. Establish Session in Backend
        session_res = requests.post(f"{API_BASE}/auth/session", json={"access_token": access_token})
        if session_res.status_code != 200:
            print(f"Failed to establish backend session: {session_res.text}")
            continue
            
        cookies = session_res.cookies
        
        print(f"Session established. Creating workspace '{c['company']}'...")
        
        # 3. Create Company
        company_payload = {
            "name": c["company"],
            "gstin": c["gstin"],
            "address": "Test Address"
        }
        
        comp_res = requests.post(f"{API_BASE}/companies", json=company_payload, cookies=cookies)
        
        if comp_res.status_code in [200, 201]:
            print(f"Successfully onboarded {c['email']} with {c['company']}")
        else:
            print(f"Failed to create company: {comp_res.text}")

if __name__ == "__main__":
    register_and_onboard()
