import streamlit as st
import json
import re
from google import genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Vedonyam - USA Lead Extractor", layout="wide")
st.title("🚀 Vedonyam FB Comments USA Lead Extractor")

# ----------------- AUTHENTICATIONS & HANDSHAKE -----------------
try:
    # 1. Gemini API Auth
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    if not GEMINI_API_KEY:
        st.error("Missing GEMINI_API_KEY in Secrets!")
        st.stop()
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 2. Google Sheets Authentication (Clean fallback mechanism)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Check if raw JSON string exists in secrets
    raw_creds = st.secrets.get("GOOGLE_CREDS_JSON", "")
    if raw_creds:
        creds_dict = json.loads(raw_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
    else:
        st.error("Google credentials configuration not found. Please set GOOGLE_CREDS_JSON in Streamlit secrets.")
        st.stop()
except Exception as auth_err:
    st.error(f"Initialization Error: Please check Streamlit Secrets Configuration! Details: {auth_err}")
    st.stop()

# ----------------- UI INPUTS -----------------
st.sidebar.header("Target Configuration")
niche_type = st.sidebar.selectbox("Select Target Niche", ["Roofing", "HVAC", "Plumbing", "General Contractor"])
extraction_mode = st.sidebar.radio("Extraction Mode", ["Paste Cleaned HTML (Safest & Highly Recommended)", "Auto Live Scrape (Requires session cookies)"])

# ----------------- DATA PROCESSING FUNCTIONS -----------------
def extract_leads_from_html(html_content):
    """
    Highly optimized parser: Minimal RAM usage, filters junk instantly.
    """
    soup = BeautifulSoup(html_content, 'lxml' if 'lxml' in globals() else 'html.parser')
    extracted_data = []
    
    # Facebook comments containers ko directly target karna for faster speed
    comment_blocks = soup.find_all(['div', 'span'], attrs={"dir": "auto"})
    
    for block in comment_blocks:
        text = block.get_text().strip()
        if len(text) > 12:  # Non-useful small text ko filter out karna CPU/RAM bachane ke liye
            # Profile link dhoondhne ke liye uske parent anchor tags check karna
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
            
    # Remove duplicates to optimize data size
    unique_data = {item['text']: item['profile_link'] for item in extracted_data}
    return [{"text": k, "profile_link": v} for k, v in unique_data.items()]

def analyze_and_qualify_with_gemini(data_list, niche):
    """
    Fast processing instructions for Gemini to target USA Contractors, Category/Sub-category, and Sale Type.
    """
    prompt = f"""
    Analyze the following raw comments/texts from Facebook.
    
    Your absolute target: Filter and extract ONLY contractors or prospects/clients based in the UNITED STATES (USA). Ignore other countries.
    If the location cannot be determined but the business structure fits USA terminology (e.g., LLC, State-specific references, zip codes), include them.

    For each valid lead, extract these precise fields in a JSON array format:
    - 'name': Profile Name
    - 'role_or_need': 'Contractor' or 'Prospect'
    - 'category': Main Business Category (e.g., Roofing, HVAC, Plumbing)
    - 'sub_category': Specific trade (e.g., Metal Roofing, AC Installation, Drain Cleaning)
    - 'is_sale_post': 'Yes' (if post/comment is selling services/products) or 'No'
    - 'business_name': Company Name (or 'N/A')
    - 'contact_info': Phone/Email/Website (or 'N/A')
    - 'snippet_context': 1 short sentence summary of their comment

    Raw Data to process:
    {json.dumps(data_list[:40])}  # Fast batch size of 40
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
        st.error(f"Gemini Processing Error: {e}")
        return []

# ----------------- APP BODY -----------------
if extraction_mode == "Paste Cleaned HTML (Safest & Highly Recommended)":
    st.info("💡 **Highly Optimized Mode:** Local browser se comments HTML paste karein. Low memory par bhi fast extract hoga.")
    
    # Links manually input karne ke liye columns taaki targeting easy ho jaye
    col1, col2 = st.columns(2)
    with col1:
        group_link_input = st.text_input("Group Link:", placeholder="https://www.facebook.com/groups/...")
    with col2:
        post_link_input = st.text_input("Post Link:", placeholder="https://www.facebook.com/groups/.../posts/...")

    html_input = st.text_area("Paste FB Comments HTML Section here:", height=200)
    
    if st.button("Extract & Qualify USA Leads 🚀"):
        if html_input.strip() == "":
            st.warning("Please paste some HTML content first!")
        else:
            with st.spinner("Processing HTML (RAM-Saving Mode)..."):
                raw_data = extract_leads_from_html(html_input)
                st.success(f"Extracted {len(raw_data)} unique text blocks!")
            
            if len(raw_data) > 0:
                with st.spinner("AI Analysis (USA Filters, Categories & Links Mapping)..."):
                    # Raw texts filter karke analyze karna
                    text_only_list = [item["text"] for item in raw_data]
                    qualified_leads = analyze_and_qualify_with_gemini(raw_data, niche_type)
                    
                    if qualified_leads:
                        # Profile link back-map karna
                        for lead in qualified_leads:
                            lead["group_link"] = group_link_input if group_link_input else "N/A"
                            lead["post_link"] = post_link_input if post_link_input else "N/A"
                            
                            # Matching profile link from HTML parsing
                            matching_link = "N/A"
                            for item in raw_data:
                                if lead["name"].lower() in item["text"].lower():
                                    matching_link = item["profile_link"]
                                    break
                            lead["profile_link"] = matching_link
                        
                        df = pd.DataFrame(qualified_leads)
                        
                        # Displaying final table with all your targeted fields
                        st.subheader("🎯 USA Leads Qualified by AI")
                        st.dataframe(df[[
                            "name", "role_or_need", "category", "sub_category", 
                            "is_sale_post", "business_name", "contact_info", 
                            "snippet_context", "profile_link", "post_link", "group_link"
                        ]])
                        
                        # Google Sheets Export
                        try:
                            sheet_name = "Vedonyam_Master_Leads_Optimize_My_GBP"
                            sheet = gc.open(sheet_name).sheet1
                            
                            for lead in qualified_leads:
                                row = [
                                    lead.get("name", "N/A"),
                                    lead.get("role_or_need", "N/A"),
                                    lead.get("category", "N/A"),
                                    lead.get("sub_category", "N/A"),
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
                            st.success(f"Successfully exported {len(qualified_leads)} targeted USA leads to Google Sheets!")
                        except Exception as sheet_err:
                            st.error(f"Failed to export to Google Sheet: {sheet_err}")
                    else:
                        st.info("AI did not detect any direct USA contractor/prospect profiles in these snippets.")
