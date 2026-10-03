import streamlit as st
import os
import contextlib
from run_automation import process_new_orders

st.set_page_config(page_title="Bakery Automation", page_icon="🍞", layout="centered")

# Ensure Streamlit secrets are pushed into environment variables for the scraper
# (st.secrets raises if no secrets.toml exists, e.g. when running locally with .env)
try:
    for key in ["CATERTRAX_URLS", "CATERTRAX_USERNAME", "CATERTRAX_PASSWORD", "GEMINI_API_KEY"]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass

# Auto-install Playwright browsers for Streamlit Community Cloud
@st.cache_resource
def install_playwright():
    os.system("playwright install chromium")
    
install_playwright()

st.title("🍞 Catertrax Bakery Automation")
st.write("Automatically calculate daily bread production based on real-time Catertrax invoices.")

if st.button("Run Bakery Automation", type="primary"):
    log_container = st.empty()
    
    # Custom redirect to show print statements in Streamlit in real-time
    class StreamlitRedirect:
        def __init__(self):
            self.log_text = ""
            
        def write(self, string):
            self.log_text += string
            # Update the Streamlit text box (keep only the last 3000 chars to avoid UI lag)
            log_container.code(self.log_text[-3000:], language='text')
            
        def flush(self):
            pass

    filepath = None
    with st.spinner("🤖 The robot is currently sweeping the Catertrax sites..."):
        with contextlib.redirect_stdout(StreamlitRedirect()):
            try:
                filepath = process_new_orders()
            except Exception as e:
                st.error(f"Automation failed with error: {e}")
                
    if filepath and os.path.exists(filepath):
        st.success("✅ Automation completed successfully!")
        
        with open(filepath, "rb") as f:
            st.download_button(
                label="📥 Download Excel Sheet",
                data=f,
                file_name=os.path.basename(filepath),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("Automation finished, but no Excel file was generated. This might happen if there are zero valid orders for today's baking offsets.")
