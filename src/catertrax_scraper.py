import os
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
import time

load_dotenv()

class CatertraxScraper:
    def __init__(self, url):
        self.url = url
        self.username = os.getenv("CATERTRAX_USERNAME")
        self.password = os.getenv("CATERTRAX_PASSWORD")
        
        # Fallback to Streamlit secrets
        if not self.username or not self.password:
            try:
                import streamlit as st
                self.username = st.secrets.get("CATERTRAX_USERNAME", self.username)
                self.password = st.secrets.get("CATERTRAX_PASSWORD", self.password)
            except Exception:
                pass

    def get_new_orders(self):
        """
        Logs into Catertrax, navigates to the orders page, and extracts new order items.
        Returns a dictionary: { "order_id": {"date": "...", "items": [{"name": "...", "qty": 1}]} }
        """
        if not self.username or not self.password:
            print("Catertrax credentials not found. Set CATERTRAX_USERNAME and CATERTRAX_PASSWORD in .env or Streamlit secrets.")
            return {}

        new_orders = {}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                print(f"Logging in to {self.url}...")
                page.goto(self.url)
                page.fill('#usernameInput', self.username)
                page.fill('#passwordInput', self.password)
                page.click('#adminSignInButton')
                page.wait_for_load_state('networkidle')
                time.sleep(2) # Give frames a moment to load
                
                print("Checking calendar for all orders this week...")
                
                # Get base url
                from urllib.parse import urlparse
                parsed_url = urlparse(self.url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                # Find the mainFrame which holds the calendar/orders
                order_urls = []
                for frame in page.frames:
                    if "mainFrame" in frame.name or "shopa_displaycalendar" in frame.url:
                        links = frame.locator('a').all()
                        for link in links:
                            href = link.get_attribute('href')
                            if href and "shopa_formatorder.asp" in href:
                                full_url = href if href.startswith("http") else f"{base_url}/{href.lstrip('/')}"
                                if full_url not in order_urls:
                                    order_urls.append(full_url)
                
                print(f"Found {len(order_urls)} orders to process.")
                
                from bs4 import BeautifulSoup
                import re
                
                for order_url in order_urls:
                    # Extract Order ID from URL
                    order_id_match = re.search(r'oid=(\d+)', order_url)
                    if not order_id_match:
                        continue
                    order_id = order_id_match.group(1)
                    
                    print(f"Extracting Order #{order_id}...")
                    page.goto(order_url)
                    page.wait_for_load_state('networkidle')
                    
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    
                    items = []
                    for t in soup.find_all('table', class_='invoiceProductTable'):
                        text = t.text.strip()
                        if 'Qty.' in text:
                            parts = re.split(r'\s*Qty\.\s*', text, 1)
                            if len(parts) == 2:
                                name = parts[0].strip()
                                qty_str = parts[1].split('Price')[0].strip()
                                try:
                                    items.append({'name': name, 'qty': int(qty_str)})
                                except:
                                    pass
                                    
                    # Extract Delivery Date and Location
                    delivery_date = time.strftime("%Y-%m-%d") # default
                    location = "Unknown"
                    try:
                        full_text = soup.get_text()
                        match = re.search(r'Pick-up/\s+Delivery Date:\s*([A-Za-z]+,\s*\d+/\d+/\d+)', full_text)
                        if match:
                            delivery_date = match.group(1).strip()
                            
                        # Extract Location (Verde, Union Kitchen, Union Burger, Eagle, Bruce, Avesta, Foodcourt)
                        loc_match = re.search(r'(Verde|Union Kitchen|Union Burger|Eagle|Bruce|Avesta|Foodcourt)', full_text, re.IGNORECASE)
                        if loc_match:
                            location = loc_match.group(1).title()
                    except Exception as e:
                        pass
                    
                    if items:
                        new_orders[order_id] = {
                            "date": delivery_date,
                            "location": location,
                            "items": items
                        }
                
                browser.close()
                
        except Exception as e:
            print(f"An error occurred during scraping: {e}")

        return new_orders

if __name__ == "__main__":
    url = os.getenv("CATERTRAX_URLS", "https://untfoodtogo.catertrax.com/shopcatertrax.asp").split(",")[0].strip()
    scraper = CatertraxScraper(url)
    orders = scraper.get_new_orders()
    print("Found orders:", orders)
