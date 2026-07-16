import os
import shutil

# Automatic Secrets Fixer for Render
if os.path.exists("secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    shutil.copy("secrets.toml", ".streamlit/secrets.toml")

# 🚀 NAYA CODE: Automatic Playwright Browser Installer
try:
    import playwright
    # Check if browser is already installed, if not, install it
    os.system("playwright install chromium")
except Exception as e:
    print(f"Playwright install error: {e}")

import os
import shutil

# Automatic Secrets Synchronizer for Render Cloud
if os.path.exists("secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    shutil.copy("secrets.toml", ".streamlit/secrets.toml")
import os
import shutil

# Automatic Secrets Fixer for Render
if os.path.exists("secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    shutil.copy("secrets.toml", ".streamlit/secrets.toml")
import streamlit as st
import asyncio
import random
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

# Page Configurations
st.set_page_config(page_title="Vedonyam Lead Core", page_icon="🛡️", layout="centered")
st.title("🛡️ Vedonyam Autonomous Leads & Project System")
st.markdown("---")

# 1. AUTHENTICATIONS & CLOUD HANDSHAKE
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Google Sheets Security Connection
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDS_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
except Exception as auth_err:
    st.error(f"Initialization Error: Please check Streamlit Secrets! ({auth_err})")

# 2. UNDERCOVER CLOUD BROWSER (COOKIE INJECTION ENGINE)
async def run_cloud_crawler(target_url, cookies_json_str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        # Inject Active Session Tokens
        if cookies_json_str:
            try:
                cookies = json.loads(cookies_json_str)
                
                # 🚀 Cookies sameSite fix karne ka automatic logic yahan set ho gaya hai
                if isinstance(cookies, list):
                    for cookie in cookies:
                        if "sameSite" in cookie:
                            val = str(cookie["sameSite"]).lower()
                            if val == "lax":
                                cookie["sameSite"] = "Lax"
                            elif val == "strict":
                                cookie["sameSite"] = "Strict"
                            elif val == "none":
                                cookie["sameSite"] = "None"
                            else:
                                del cookie["sameSite"]
                                
                await context.add_cookies(cookies)
            except Exception as e:
                st.error(f"Invalid Cookie JSON Format: {e}")
                return None

                
        page = await context.new_page()
        st.info("🔄 Cloud agent is browsing target portal undercover...")
        
                # Network slow hone par bhi pipeline na ruke, isliye timeout 90 seconds kiya aur networkidle lagaya
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=90000)
        except Exception as e:
            # Agar domcontentloaded tak bhi load ho jaye toh safe side par proceed karein
            st.warning("⚠️ Network slow hai, par data extraction check kar rahe hain...")

        await asyncio.sleep(random.randint(5, 10)) 
        
        for i in range(random.randint(3, 5)):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.6);")
            await asyncio.sleep(random.randint(3, 7))
            
        html_content = await page.content()
        await context.close()
        return html_content

# 3. INTERFACE CONTROLS
st.subheader("🎯 Configure Pipeline Parameters")
category = st.selectbox("Select Trade/Niche:", ["Roofing", "Plumbing", "Fencing", "Painting", "General Construction"])
fb_link = st.text_input("Enter Target Link (Facebook Post/Group/Project Page):")
fb_cookies = st.text_area("Paste FB Session Cookies (Copy from EditThisCookie):", height=150)

if st.button("🚀 Launch Autonomous Extraction"):
    if not fb_link or not fb_cookies:
        st.warning("Please fill out both the URL field and the Session Cookies box.")
    else:
        with st.spinner("Agent working on cloud... Please wait..."):
            try:
                raw_html = asyncio.run(run_cloud_crawler(fb_link, fb_cookies))
                
                if not raw_html:
                    st.error("Could not fetch page contents.")
                    st.stop()
                    
                soup = BeautifulSoup(raw_html, 'html.parser')
                clean_text = soup.get_text(separator=' ', strip=True)
                
                st.info("🧠 Brain Core analyzing posts and buyer urgency...")
                system_instruction = (
                    "You are the elite backend lead qualification system for Vedonyam Marketing. "
                    "Analyze the scraped web content. Identify hungry contractors, active job posts, or project requests. "
                    "Extract: Contractor/Client Name, Contact info/Profile link, Estimated Lead Value (between $30 and $100 based on urgency), "
                    "and write a high-converting, tailored pitch script for outreach. "
                    "Output MUST be a strict JSON array of objects with keys: contractor_name, profile_link, contact_info, estimated_lead_value_usd, custom_dm_script."
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash-2026',

                    contents=f"Extract and script valid leads for {category} from this feed:\n{clean_text[:40000]}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction, 
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                
                raw_response = response.text.strip()
                extracted_leads = json.loads(raw_response)
                
                if not extracted_leads:
                    st.warning("AI did not find any matching leads in this text snippet.")
                else:
                    st.info("📝 Injecting clean records into Google Sheet...")
                    spreadsheet = gc.open("Vedonyam_Master_Leads_Optimize_My_GBP")
                    
                    current_date = datetime.datetime.now().strftime("%d_%b_%Y")
                    tab_name = f"{category}_{current_date}"
                    
                    try:
                        worksheet = spreadsheet.worksheet(tab_name)
                    except gspread.exceptions.WorksheetNotFound:
                        worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="7")
                        worksheet.append_row(["Timestamp", "Contractor Name", "Profile/Post Link", "Contact Info", "Lead Value ($)", "Custom Pitch Script", "Status"])
                    
                    for lead in extracted_leads:
                        worksheet.append_row([
                            str(datetime.datetime.now()),
                            lead.get("contractor_name", "N/A"),
                            lead.get("profile_link", "N/A"),
                            lead.get("contact_info", "N/A"),
                            lead.get("estimated_lead_value_usd", "50"),
                            lead.get("custom_dm_script", "N/A"),
                            "Fresh / Not Contacted"
                        ])
                        
                    st.success(f"🎉 Success! {len(extracted_leads)} qualified leads synced into Sheet tab: '{tab_name}'!")
                    
            except Exception as pipeline_error:
                st.error(f"Pipeline Interrupted: {pipeline_error}")
