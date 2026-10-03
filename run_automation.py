import time
import os
from src.catertrax_scraper import CatertraxScraper
from src.bread_mapper import BreadMapper
from src.excel_generator import SpreadsheetManager
from urllib.parse import urlparse
from datetime import datetime, timedelta

def process_new_orders():
    print("Starting offset-matrix order processing cycle...")
    
    urls_env = os.getenv("CATERTRAX_URLS")
    if urls_env:
        urls = [u.strip() for u in urls_env.split(',')]
    else:
        urls = [os.getenv("CATERTRAX_URL", "https://untfoodtogo.catertrax.com/shopcatertrax.asp")]

    mapper = BreadMapper()
    spreadsheet = SpreadsheetManager()

    now = datetime.now()
    start_date = now.date()
    weekday = now.strftime("%A")

    # Define Offset Matrix
    # offsets[weekday]["category"] = list of target days offset from today
    offsets = {
        "Monday": {
            "foodcourt": [0],
            "retail": [1],
            "catering": [2],
            "catering_pizza": [2],
            "box_lunch": [3],
            "french_toast": [4]
        },
        "Tuesday": {
            "foodcourt": [0],
            "retail": [1],
            "catering": [2],
            "catering_pizza": [2],
            "box_lunch": [3],
            "french_toast": [4, 5, 6]
        },
        "Wednesday": {
            "foodcourt": [0],
            "retail": [1],
            "catering": [2],
            "catering_pizza": [2],
            "box_lunch": [3, 4, 5],
            "french_toast": [6]
        },
        "Thursday": {
            "foodcourt": [0],
            "retail": [1],
            "catering": [2, 3, 4],
            "catering_pizza": [4],
            "box_lunch": [5],
            "french_toast": [6]
        },
        "Friday": {
            "foodcourt": [0],
            "retail": [2, 3],
            "catering": [4],
            "catering_pizza": [4],
            "box_lunch": [5],
            "french_toast": [6]
        },
        "Saturday": {
            "foodcourt": [], "retail": [], "catering": [], "catering_pizza": [], "box_lunch": [], "french_toast": []
        },
        "Sunday": {
            "foodcourt": [], "retail": [], "catering": [], "catering_pizza": [], "box_lunch": [], "french_toast": []
        }
    }
    
    today_offsets = offsets.get(weekday, offsets["Monday"])

    for url in urls:
        print(f"\n--- Processing Site: {url} ---")
        site_name = urlparse(url).netloc.split('.')[0]
        
        scraper = CatertraxScraper(url)
        orders = scraper.get_new_orders()
        
        if not orders:
            print(f"No new orders found for {site_name}.")
            continue

        for order_id, order_data in orders.items():
            date_str = order_data.get("date")
            location = order_data.get("location", "Unknown")
            items = order_data.get("items", [])
            
            try:
                if "," in date_str:
                    date_part = date_str.split(",")[1].strip()
                    order_date_obj = datetime.strptime(date_part, "%m/%d/%Y").date()
                else:
                    order_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                offset_days = (order_date_obj - start_date).days
            except Exception as e:
                print(f"Warning: Could not parse date '{date_str}' for order #{order_id}. Skipping.")
                continue

            preparations = []
            for item in items:
                name = item.get("name")
                qty = item.get("qty")
                name_lower = name.lower()
                
                # Determine Category and check if offset_days is allowed
                is_allowed = False
                
                if site_name == "verdeonline":
                    if "sandwich express box lunch" in name_lower:
                        if offset_days in today_offsets["box_lunch"]:
                            is_allowed = True
                    elif "french toast" in name_lower:
                        if offset_days in today_offsets["french_toast"]:
                            is_allowed = True
                    elif "pizza" in name_lower:
                        if offset_days in today_offsets["catering_pizza"]:
                            is_allowed = True
                    else:
                        if offset_days in today_offsets["catering"]:
                            is_allowed = True
                
                elif site_name == "untfoodtogo":
                    loc_upper = location.upper()
                    
                    if "EAGLE" in loc_upper or "BRUCE" in loc_upper:
                        continue
                    
                    if "french toast" in name_lower:
                        if offset_days in today_offsets["french_toast"]:
                            is_allowed = True
                    elif "FOODCOURT" in loc_upper:
                        if offset_days in today_offsets["foodcourt"]:
                            is_allowed = True
                    else:
                        if offset_days in today_offsets["retail"]:
                            is_allowed = True
                
                if not is_allowed:
                    continue
                
                prep_details = mapper.calculate_bread_needs(name, qty, site_name)
                if prep_details:
                    preparations.append(prep_details)
                    print(f"Mapped: {name} (Qty {qty}) -> {prep_details['bread_qty']} {prep_details['bread_unit']} of {prep_details['bread_needed']}")

            if preparations:
                full_order_id = f"{site_name}-{order_id}"
                spreadsheet.append_order_preparations(site_name, location, full_order_id, date_str, preparations)

    return spreadsheet.filepath

if __name__ == "__main__":
    print("--- Catertrax Bread Order Automation ---")
    process_new_orders()
