import streamlit as st
import json
import re
from google import genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(
    page_title="Vedonyam - Mobile/PC Lead Extractor", 
    layout="wide",
    initial_sidebar_state="collapsed" # Mobile par sidebar auto-collapse ho jayega screen space bachane ke liye
)

# Responsive & Flat UI Customization for Mobile + Laptop
st.markdown("""
    <style>
        .block-container { padding: 1rem 1rem; }
        .stButton>button { width: 100%; border-radius: 8px; height: 3rem; font-size: 16px; font-weight: bold; }
        div[data-testid="stTextArea"] textarea { font-size: 14px; }
        .stDataFrame { width: 100% !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Vedonyam FB Lead Pro (Mobile & PC)")
st.markdown("---")

# ----------------- AUTHENTICATIONS -----------------
@st.cache_resource
def init_connections():
    try:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
        if not GEMINI_API_KEY:
            return None, "Missing GEMINI_API_KEY"
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

# ----------------- UI CONFIGURATION -----------------
categories_list = [
    "Roofing", "HVAC", "Plumbing", "General Contractor", "Electrical", 
    "Landscaping & Lawn Care", "Painting & Wallcovering", "Masonry & Brickwork", 
    "Siding & Gutters", "Flooring & Tiling", "Drywall & Plastering", 
    "Fencing & Decking", "Concrete & Paving", "Carpentry & Framing", 
    "Demolition & Excavation", "Waterproofing & Foundation", "Pest Control", 
    "Cleaning & Pressure Washing", "Solar Installation", "Window & Door Installation", 
    "Remodeling & Renovation", "Tree Services"
]

niche_type = st.selectbox("🎯 Select Target Niche", categories_list)

group_link_input = st.text_input("🔗 FB Group Link (Optional):", placeholder="https://...")
post_link_input = st.text_input("📌 FB Post Link (Optional):", placeholder="https://...")

html_input = st.text_area("📄 Paste FB Comments HTML Source (or clean text):", height=200)

# ----------------- SOFT & FAST PROCESSING -----------------
def process_data_soft(html_content):
    # Soft pre-cleaning using simple regex to avoid RAM freeze
    cleaned = re.sub(r'<(script|style|svg|path|canvas|iframe)[^>]*?>([\s\S]*?)</\1>', '', html_content)
    soup = BeautifulSoup(cleaned, 'html.parser')
    
    extracted = []
    # Targeted search directly for text containers to save memory
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
            
    # Quick duplicate remove
    seen = set()
    unique_data = []
    for item in extracted:
        if item['text'] not in seen:
            seen.add(item['text'])
            unique_data.append(item)
    return unique_data

def analyze_gemini_fast(data_list, niche):
    prompt = f"""
    Analyze these Facebook snippets. Extract ONLY contractors or prospects located in the USA.
    Categorize them strictly using:
    Main Categories: Roofing, HVAC, Plumbing, General Contractor, Electrical, Landscaping, Painting, Masonry, Siding, Flooring, Drywall, Fencing, Concrete, Carpentry, Demolition, Waterproofing, Pest Control, Cleaning, Solar, Window/Door, Remodeling, Tree Services.
    
    Output a valid JSON array with exact keys:
    'name', 'role_or_need' ('Contractor' or 'Prospect'), 'category', 'sub_category', 'location', 'is_sale_post' ('Yes' or 'No'), 'business_name', 'contact_info', 'snippet_context'.
    
    Data: {json.dumps(data_list[:35])}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        res_text = response.text.strip()
        match = re.search(r"\[\s*\{.*\}\s*\]", res_text, re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except:
        return []

# ----------------- ACTION BUTTON -----------------
if st.button("🚀 Process & Save Leads"):
    if not html_input.strip():
        st.warning("Pehle data paste karo bhai!")
    else:
        with st.spinner("Extracting..."):
            raw_data = process_data_soft(html_input)
            
        if len(raw_data) > 0:
            with st.spinner("AI Filtering (USA Target)..."):
                qualified = analyze_gemini_fast(raw_data, niche_type)
                
                if qualified:
                    # Link mapping
                    for lead in qualified:
                        lead["group_link"] = group_link_input if group_link_input else "N/A"
                        lead["post_link"] = post_link_input if post_link_input else "N/A"
                        lead["profile_link"] = "N/A"
                        for item in raw_data:
                            if lead["name"].lower() in item["text"].lower():
                                lead["profile_link"] = item["profile_link"]
                                break
                    
                    df = pd.DataFrame(qualified)
                    st.subheader("🎯 Target USA Leads")
                    st.dataframe(df, use_container_width=True)
                    
                    # Batch Excel/Google Sheet Sync (RAM & Network friendly)
                    with st.spinner("Syncing to Google Sheets..."):
                        try:
                            sheet = gc.open("Vedonyam_Master_Leads_Optimize_My_GBP").sheet1
                            rows_to_push = []
                            for lead in qualified:
                                rows_to_push.append([
                                    lead.get("name", "N/A"), lead.get("role_or_need", "N/A"),
                                    lead.get("category", "N/A"), lead.get("sub_category", "N/A"),
                                    lead.get("location", "N/A"), lead.get("is_sale_post", "N/A"),
                                    lead.get("business_name", "N/A"), lead.get("contact_info", "N/A"),
                                    lead.get("profile_link", "N/A"), lead.get("post_link", "N/A"),
                                    lead.get("group_link", "N/A"), "FB Comments"
                                ])
                            sheet.append_rows(rows_to_push)
                            st.success(f"🔥 Successfully saved {len(qualified)} Leads!")
                        except Exception as e:
                            st.error(f"Sheet Sync Error: {e}")
                else:
                    st.info("No active USA leads detected.")
        else:
            st.info("No text extracted. Check HTML.")
