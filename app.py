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

st.set_page_config(page_title="Vedonyam - Anti-Ban USA Bot", layout="wide")
st.title("🛡️ Vedonyam Anti-Ban Autonomous FB Bot")
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
target_url = st.text_input("🔗 Target FB URL:", placeholder="https://www.facebook.com/...")

# Premium Cookie Security Input
fb_cookie = st.text_input("🍪 Paste FB Cookie String (e.g., c_user=...; xs=...;):", type="password")

# ----------------- SAFE COOKIE BOT ENGINE -----------------
def run_safe_cookie_bot(url, cookie_str, scrolls=4):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    # Step 1: Hit domain first to inject cookies
    driver.get("https://www.facebook.com")
    time.sleep(2)
    
    # Step 2: Parse and inject cookie string securely
    try:
        matches = re.findall(r'([^=;\s]+)=([^;]+)', cookie_str)
        for name, value in matches:
            driver.add_cookie({"name": name, "value": value, "domain": ".facebook.com"})
        st.info("🔒 Session cookies injected safely into stealth browser container.")
    except Exception as ce:
        st.error(f"Cookie Injection Format Error: {ce}")
        driver.quit()
        return ""

    # Step 3: Open target link as a logged-in trusted human account
    driver.get(url)
    time.sleep(random.uniform(5.1, 7.3))
    
    # Auto-scrolling and revealing comments smoothly
    for i in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(3.5, 5.5)) # Variable dynamic delays to mimic human behavior
        
        try:
            more_comments = driver.find_elements(By.XPATH, "//span[contains(text(), 'View more comments') or contains(text(), 'Write a comment')]")
            if more_comments:
                driver.execute_script("arguments[0].click();", more_comments[0])
                time.sleep(random.uniform(2.0, 4.0))
        except:
            pass
            
    raw_html = driver.page_source
    driver.quit()
    return raw_html

# ----------------- PARSING & AI LOGIC -----------------
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

# ----------------- TRIGGER ACTION -----------------
if st.button("🛡️ Launch Shielded Automation"):
    if not target_url.strip() or not fb_cookie.strip():
        st.warning("Bhai, Target URL aur FB Cookie string dono mandatory hain safety ke liye!")
    else:
        with st.status("🕵️ Executing Anti-Ban Identity Protocol...", expanded=True) as status:
            status.write("Initializing trusted user session...")
            page_html = run_safe_cookie_bot(target_url, fb_cookie, scrolls=4)
            
            if not page_html:
                status.update(label="Session crashed due to cookie error.", state="error")
                st.stop()
                
            status.write("Reading hidden visual data fields...")
            raw_data = extract_html_data(page_html)
            
            status.write("Gemini Engine parsing target niches...")
            qualified = analyze_gemini(raw_data)
            
            if qualified:
                df = pd.DataFrame(qualified)
                st.subheader("🎯 Safe Qualified USA Leads")
                st.dataframe(df, use_container_width=True)
                
                status.write("Pushed new rows to your master tracking sheet...")
                try:
                    sheet = gc.open("Vedonyam_Master_Leads_Optimize_My_GBP").sheet1
                    rows = [[l.get("name","N/A"), l.get("role_or_need","N/A"), l.get("category","N/A"), 
                             l.get("sub_category","N/A"), l.get("location","N/A"), l.get("is_sale_post","N/A"), 
                             l.get("business_name","N/A"), l.get("contact_info","N/A"), l.get("profile_link","N/A"), 
                             target_url, "Shielded Cookie Bot"] for l in qualified]
                    sheet.append_rows(rows)
                    status.update(label="🔥 Data Synced Securely! Account Safe.", state="complete")
                except Exception as e:
                    st.error(f"Sheet Error: {e}")
            else:
                status.update(label="Analysis done. No USA contractors caught in this run.", state="complete")
