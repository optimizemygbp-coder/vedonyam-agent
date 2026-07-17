import streamlit as st
import json
import re
from google import genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import pandas as pd
import time

st.set_page_config(
    page_title="Vedonyam - USA Lead Extractor Pro", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium UI Styling
st.markdown("""
    <style>
        .reportview-container { background: #f5f7f9; }
        .main-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Vedonyam FB Comments USA Lead Extractor")
st.markdown("---")

# ----------------- AUTHENTICATIONS & HANDSHAKE -----------------
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if not GEMINI_API_KEY:
        st.error("Missing GEMINI_API_KEY in Secrets!")
        st.stop()
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    raw_creds = st.secrets.get("GOOGLE_CREDS_JSON", "")
    if raw_creds:
        creds_dict = json.loads(raw_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
    else:
        st.error("Google credentials configuration not found.")
        st.stop()
except Exception as auth_err:
    st.error(f"Initialization Error: {auth_err}")
    st.stop()

# ----------------- UI INPUTS (SIDEBAR) -----------------
st.sidebar.image("https://img.icons8.com/clouds/100/000000/database.png", width=100)
st.sidebar.header("Target Configuration")

# 20+ Main Categories dynamically mapped in UI
categories_list = [
    "Roofing", "HVAC", "Plumbing", "General Contractor", "Electrical", 
    "Landscaping & Lawn Care", "Painting & Wallcovering", "Masonry & Brickwork", 
    "Siding & Gutters", "Flooring & Tiling", "Drywall & Plastering", 
    "Fencing & Decking", "Concrete & Paving", "Carpentry & Framing", 
    "Demolition & Excavation", "Waterproofing & Foundation", "Pest Control", 
    "Cleaning & Pressure Washing", "Solar Installation", "Window & Door Installation", 
    "Remodeling & Renovation", "Tree Services"
]
niche_type = st.sidebar.selectbox("Select Target Niche", categories_list)
extraction_mode = st.sidebar.radio("Extraction Mode", ["Paste Cleaned HTML (Safest & Fast)", "Auto Live Scrape"])

# ----------------- OPTIMIZED DATA PROCESSING -----------------
def clean_and_extract_html_fast(html_content):
    cleaned_html = re.sub(r'<(script|style|svg|path|canvas|iframe)[^>]*>([\s\S]*?)<\/\1>', '', html_content)
    soup = BeautifulSoup(cleaned_html, 'html.parser')
    extracted_data = []
    
    comment_blocks = soup.find_all(['div', 'span'], attrs={"dir": "auto"})
    total_blocks = len(comment_blocks)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, block in enumerate(comment_blocks):
        if idx % max(1, total_blocks // 10) == 0:
            pct = int((idx / total_blocks) * 100)
            progress_bar.progress(pct)
            status_text.text(f"Parsing HTML Elements... {pct}%")
            
        text = block.get_text().strip()
        if len(text) > 12:
            profile_link = "N/A"
            parent_a = block.find_parent('a') or (block.find_previous('a') if hasattr(block, 'find_previous') else None)
            if parent_a and parent_a.has_attr('href'):
                href = parent_a['href']
                if "facebook.com" in href or "/user/" in href or "profile.php" in href:
                    profile_link = href if href.startswith("http") else f"https://www.facebook.com{href}"
            
            extracted_data.append({
                "text": text,
                "profile_link": profile_link
            })
            
    progress_bar.progress(100)
    status_text.text("HTML Parsed and Cleaned Successfully! 🎯")
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()
    
    unique_data = {item['text']: item['profile_link'] for item in extracted_data}
    return [{"text": k, "profile_link": v} for k, v in unique_data.items()]

def analyze_and_qualify_with_gemini(data_list, niche):
    prompt = f"""
    Analyze the following raw Facebook comments/posts data.
    
    CRITICAL TARGET: Find and qualify ONLY contractors or prospects/clients based in the UNITED STATES (USA).
    If it is NOT in the USA or has no USA context, exclude it.

    You must map the data strictly to the following taxonomy:
    
    MAIN CATEGORIES (20+):
    Roofing, HVAC, Plumbing, General Contractor, Electrical, Landscaping & Lawn Care, Painting & Wallcovering, Masonry & Brickwork, Siding & Gutters, Flooring & Tiling, Drywall & Plastering, Fencing & Decking, Concrete & Paving, Carpentry & Framing, Demolition & Excavation, Waterproofing & Foundation, Pest Control, Cleaning & Pressure Washing, Solar Installation, Window & Door Installation, Remodeling & Renovation, Tree Services.

    SUB-CATEGORIES (50+ Reference):
    Metal Roofing, Asphalt Shingle, Tile Roof, Flat Roof Repair, AC Repair, Furnace Installation, Commercial HVAC, Residential Plumbing, Drain Cleaning, Emergency Plumber, Home Remodeling, Deck Building, Concrete Driveways, Asphalt Paving, Panel Upgrade, Lighting Design, House Painting, Commercial Painting, Siding Repair, Gutter Cleaning, Tile Installation, Hardwood Flooring, Drywall Patching, Retaining Walls, Tree Removal, Stump Grinding, Lawn Mowing, Landscape Design, Brick Repair, Concrete Pouring, Kitchen Remodeling, Bathroom Renovation, Solar Panel Maintenance, Window Replacement, Entry Door Setup, Crawlspace Encapsulation, Foundation Repair, Termite Control, Bedbug Treatment, Pressure Washing, Roof Soft Wash, Window Cleaning, Attic Insulation, Fence Installation, Structural Framing, Trim Carpentry, Shed Building, Pool Deck Repair, Epoxy Flooring, Asbestos Removal.

    Extract these exact fields in a clean JSON array structure:
    - 'name': Profile Name
    - 'role_or_need': Must be 'Contractor' or 'Prospect'
    - 'category': Choose best-fit from Main Categories
    - 'sub_category': Choose best-fit from Sub-Categories (or specify precisely if not listed)
    - 'location': Extract the Area/City/State in the USA (e.g., Dallas, TX or Orlando, FL). If state/city isn't explicitly mentioned, try to infer from area codes or local indicators, else mark "USA"
    - 'is_sale_post': 'Yes' (if trying to sell something) or 'No'
    - 'business_name': Company Name (or 'N/A')
    - 'contact_info': Phone/Email/Website (or 'N/A')
    - 'snippet_context': 1 short sentence summary of their comment

    Raw Texts to Analyze:
    {json.dumps(data_list[:40])}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        response_text = response.text.strip()
        match = re.search(r"\[\s*\{.*\}\s*\]", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return []
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return []

# ----------------- MAIN APP UI -----------------
if extraction_mode == "Paste Cleaned HTML (Safest & Fast)":
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("📋 Scraping Environment Config")
    
    col1, col2 = st.columns(2)
    with col1:
        group_link_input = st.text_input("🔗 Target Facebook Group Link:", placeholder="Enter FB Group Link")
    with col2:
        post_link_input = st.text_input("📌 Specific Post Link:", placeholder="Enter FB Post Link")
        
    html_input = st.text_area("📄 Paste FB Page/Comments HTML Source Here:", height=250)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🚀 Process & Extract USA Contractors"):
        if not html_input.strip():
            st.warning("Pehle HTML block paste karo bhai!")
        else:
            raw_data = clean_and_extract_html_fast(html_input)
            st.success(f"Extracted {len(raw_data)} unique content lines. Starting AI qualification...")
            
            if len(raw_data) > 0:
                with st.spinner("Gemini AI is analyzing & classifying leads..."):
                    qualified_leads = analyze_and_qualify_with_gemini(raw_data, niche_type)
                    
                    if qualified_leads:
                        # Link Map matching
                        for lead in qualified_leads:
                            lead["group_link"] = group_link_input if group_link_input else "N/A"
                            lead["post_link"] = post_link_input if post_link_input else "N/A"
                            
                            matching_link = "N/A"
                            for item in raw_data:
                                if lead["name"].lower() in item["text"].lower():
                                    matching_link = item["profile_link"]
                                    break
                            lead["profile_link"] = matching_link

                        df = pd.DataFrame(qualified_leads)
                        
                        # Show Visualized Premium Table
                        st.subheader("🎯 Qualified USA Leads")
                        st.dataframe(df[[
                            "name", "role_or_need", "category", "sub_category", "location",
                            "is_sale_post", "business_name", "contact_info", 
                            "snippet_context", "profile_link", "post_link", "group_link"
                        ]], use_container_width=True)
                        
                        # Google Sheets Sync
                        with st.spinner("Writing records to Master Google Sheet..."):
                            try:
                                sheet_name = "Vedonyam_Master_Leads_Optimize_My_GBP"
                                sheet = gc.open(sheet_name).sheet1
                                
                                for lead in qualified_leads:
                                    row = [
                                        lead.get("name", "N/A"),
                                        lead.get("role_or_need", "N/A"),
                                        lead.get("category", "N/A"),
                                        lead.get("sub_category", "N/A"),
                                        lead.get("location", "N/A"),
                                        lead.get("is_sale_post", "N/A"),
                                        lead.get("business_name", "N/A"),
                                        lead.get("contact_info", "N/A"),
                                        lead.get("snippet_context", "N/A"),
                                        lead.get("profile_link", "N/A"),
                                        lead.get("post_link", "N/A"),
                                        lead.get("group_link", "N/A"),
                                        "FB Comments"
                                    ]
                                    sheet.append_row(row)
                                st.success(f"🔥 Success! {len(qualified_leads)} leads pushed to Google Sheets.")
                            except Exception as sheet_err:
                                st.error(f"Google Sheet Export Error: {sheet_err}")
                    else:
                        st.info("No active USA leads matching the criteria were found in this snippet.")
