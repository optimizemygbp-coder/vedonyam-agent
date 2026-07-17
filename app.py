import streamlit as st
import json
import re
import time
import random
from google import genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import pandas as pd

# Selenium Modules
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

st.set_page_config(page_title="Vedonyam Hybrid Engine", layout="wide")
st.title("🛡️ Vedonyam Lead Gathering System (Dual-Mode)")
st.markdown("---")

# ----------------- INITIALIZATION -----------------
@st.cache_resource
def init_connections():
    try:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
        if not GEMINI_API_KEY: return None, "Missing GEMINI_API_KEY"
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_creds = st.secrets.get("GOOGLE_CREDS_JSON", "")
        if raw_creds:
            creds_dict = json.loads(raw_creds)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            gc = gspread.authorize(creds)
            return {"client": client, "gc": gc}, None
        return None, "Google Sheets Credentials Missing"
    except Exception as e:
        return None, str(e)

conns, err = init_connections()
if err:
    st.error(f"Setup Error: {err}")
    st.stop()

client = conns["client"]
gc = conns["gc"]

# ----------------- CONFIGURATION -----------------
categories_list = [
    "Roofing", "HVAC", "Plumbing", "General Contractor", "Electrical", 
    "Landscaping & Lawn Care", "Painting & Wallcovering", "Masonry & Brickwork", 
    "Siding & Gutters", "Flooring & Tiling", "Drywall & Plastering", 
    "Fencing & Decking", "Concrete & Paving", "Carpentry & Framing", 
    "Demolition & Excavation", "Waterproofing & Foundation", "Pest Control", 
    "Cleaning & Pressure Washing", "Solar Installation", "Window & Door Installation", 
    "Remodeling & Renovation", "Tree Services"
]

niche_type = st.selectbox("🎯 Target Niche", categories_list)

# DUAL MODE SELECTOR
mode = st.radio("⚙️ Operational Mode Select Karo:", ["📋 Paste Raw HTML (Instant & 100% Safe)", "🤖 Run Cloud Stealth Bot (Risk of Timeout)"])

# ----------------- SAFE COOKIE BOT ENGINE -----------------
def run_safe_cookie_bot(url, cookie_str, scrolls=3):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(50)  # Stop infinite freezing
    
    try:
        driver.get("https://www.facebook.com")
        matches = re.findall(r'([^=;\s]+)=([^;]+)', cookie_str)
        for name, value in matches:
            driver.add_cookie({"name": name, "value": value, "domain": ".facebook.com"})
        
        driver.get(url)
        time.sleep(4)
        
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        raw_html = driver.page_source
        driver.quit()
        return raw_html
    except Exception as e:
        driver.quit()
        return f"ERROR: {str(e)}"

# ----------------- DATA CLEANING ENGINE -----------------
def extract_html_data(html_content):
    cleaned = re.sub(r'<(script|style|svg|path|canvas|iframe)[^>]*?>([\s\S]*?)</\1>', '', html_content)
    soup = BeautifulSoup(cleaned, 'html.parser')
    extracted = []
    
    for element in soup.find_all(['div', 'span'], attrs={"dir": "auto"}):
        text = element.get_text().strip()
        if len(text) > 12:
            p_link = "N/A"
            parent = element.find_parent('a') or (element.find_previous('a') if hasattr(element, 'find_previous') else None)
            if parent and parent.has_attr('href'):
                href = parent['href']
                if "facebook.com" in href or "/user/" in href or "profile.php" in href:
                    p_link = href if href.startswith("http") else f"https://www.facebook.com{href}"
            extracted.append({"text": text, "profile_link": p_link})
            
    seen = set()
    unique_data = []
    for item in extracted:
        if item['text'] not in seen:
            seen.add(item['text'])
            unique_data.append(item)
    return unique_data

def analyze_gemini(data_list):
    prompt = f"""
    Analyze these raw Facebook text blocks. Extract ONLY contractors or prospects located in the USA.
    Output clean JSON array with keys: 'name', 'role_or_need', 'category', 'sub_category', 'location', 'is_sale_post', 'business_name', 'contact_info', 'snippet_context'.
    Data: {json.dumps(data_list[:35])}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        match = re.search(r"\[\s*\{.*\}\s*\]", response.text.strip(), re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except:
        return []

# ----------------- LOGIC CONDITIONAL RENDER -----------------
if mode == "🤖 Run Cloud Stealth Bot (Risk of Timeout)":
    target_url = st.text_input("🔗 Target FB URL:", placeholder="https://www.facebook.com/...")
    fb_cookie = st.text_input("🍪 Paste FB Cookie String:", type="password")
    
    if st.button("🚀 Trigger Automation"):
        if not target_url or not fb_cookie:
            st.warning("Please enter required inputs.")
        else:
            with st.status("Executing system actions...", expanded=True) as status:
                page_html = run_safe_cookie_bot(target_url, fb_cookie)
                if "ERROR" in page_html:
                    status.update(label="Cloud connection timed out/blocked by FB. Please use 'Paste Raw HTML' mode!", state="error")
                else:
                    raw_data = extract_html_data(page_html)
                    qualified = analyze_gemini(raw_data)
                    # Sync to sheet logic...
                    if qualified:
                        sheet = gc.open("Vedonyam_Master_Leads_Optimize_My_GBP").sheet1
                        rows = [[l.get("name","N/A"), l.get("role_or_need","N/A"), l.get("category","N/A"), l.get("sub_category","N/A"), l.get("location","N/A"), l.get("is_sale_post","N/A"), l.get("business_name","N/A"), l.get("contact_info","N/A"), l.get("profile_link","N/A"), target_url, "Bot Mode"] for l in qualified]
                        sheet.append_rows(rows)
                        status.update(label="Success! Pushed to Sheet.", state="complete")
                        st.dataframe(pd.DataFrame(qualified))
else:
    target_url = st.text_input("🔗 Source FB URL (For tracking):")
    html_input = st.text_area("📋 Mobile/PC se Comments ka Source Code ya Text copy karke yahan paste karo:", height=250)
    
    if st.button("🔥 Process & Push Leads"):
        if not html_input:
            st.warning("Please paste the data content!")
        else:
            with st.spinner("Processing extracted payload via Gemini AI..."):
                raw_data = extract_html_data(html_input)
                qualified = analyze_gemini(raw_data)
                if qualified:
                    sheet = gc.open("Vedonyam_Master_Leads_Optimize_My_GBP").sheet1
                    rows = [[l.get("name","N/A"), l.get("role_or_need","N/A"), l.get("category","N/A"), l.get("sub_category","N/A"), l.get("location","N/A"), l.get("is_sale_post","N/A"), l.get("business_name","N/A"), l.get("contact_info","N/A"), l.get("profile_link","N/A"), target_url, "Manual Paste"] for l in qualified]
                    sheet.append_rows(rows)
                    st.success("🎯 Data extracted successfully and sent to Google Sheets!")
                    st.dataframe(pd.DataFrame(qualified))
                else:
                    st.info("No targeted USA contractors found in this payload.")
