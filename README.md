# Catertrax Bakery Automation

## 🎯 Project Objective
The primary objective of this project is to fully automate the daily calculation of bread production for the university bakery. Previously, the bakery team had to manually log into Catertrax, scrape through hundreds of catering and retail invoices, tally up the individual sandwiches/items ordered, manually convert those items into baking recipes (e.g., converting 42 sandwiches into loaves of bread), and meticulously build a daily Excel spreadsheet. 

This robot automates that entire workflow. With a single command, it navigates the websites, extracts the orders, applies complex date-offset logic, translates the orders into raw baking quantities using customizable formulas, and outputs a perfectly formatted Excel sheet.

## 🚀 Why This Is Used
1. **Time Savings**: Turns a tedious, multi-hour daily task into a 30-second automated script.
2. **Eliminates Human Error**: Mathematical conversions (like calculating how many bins of Challah buns are needed for a catering order) are handled safely and automatically without math mistakes.
3. **Intelligent Scheduling**: The script is context-aware. If it runs on a Tuesday, it knows to pull Wednesday's Retail orders, Thursday's Catering orders, and Friday's Box Lunches. 
4. **Dynamic Scaling**: The Excel sheets build themselves. If there are no Box Lunches on a given Friday, the script intelligently leaves that column out rather than presenting a blank sheet of zeroes.

## 🏗️ Core Aspects of the Project

### 1. The Web Scraper (`src/catertrax_scraper.py`)
This module uses Playwright to launch a headless browser, log into the `verdeonline` and `untfoodtogo` Catertrax websites, and scrape the HTML of the invoices. 
It uses advanced regular expressions (Regex) to extract the **Delivery Date**, the **Location** (e.g., Avesta, Union Burger), and the exact **Quantity** of every item ordered.

### 2. The Logic Engine (`run_automation.py`)
This is the central nervous system of the project. It orchestrates the schedule. It contains the "Offset Matrix," which applies strict rules to decide *when* items need to be baked. 
- **Foodcourt** orders are processed for same-day prep (Offset: 0).
- **Retail** orders (Verde, Union Kitchen, Avesta, Union Burger) are processed for next-day prep (Offset: +1).
- **Catering & Box Lunches** are pushed further out (Offsets: +2 to +5) depending on the day of the week.
- **Dining Halls** (Eagle, Bruce) are safely ignored by the web scraper so they can be injected manually via email later.

### 3. The Bread Mapper (`src/bread_mapper.py`)
This module reads the scraped items and translates them into baking tasks. It handles partial text matching (automatically fixing hyphens and formatting) to cross-reference the invoice item against the central database (`config/mapping_rules.json`). 
Once matched, it runs an isolated Python `eval()` function to securely calculate mathematical formulas (like `math.ceil((qty*1.55)/105)`).

### 4. The Spreadsheet Generator (`src/excel_generator.py`)
Using the `pandas` library, this module takes the final translated bread lists and dynamically constructs an Excel sheet. It routes the final numbers into explicit columns (e.g., `VED`, `UNION`, `AVESTA`, `FOODCOURT`) and automatically sums the rows into a `TOTALS` column.

## 📂 Project Structure
```text
Clark_Project/
├── run_automation.py          # Main execution script (offset matrix + orchestration)
├── app.py                     # Streamlit web UI with Excel download
├── requirements.txt           # Python dependencies
├── .env.example               # Template for credentials (copy to .env)
├── config/
│   └── mapping_rules.json     # Bread names, bin sizes, and formulas
├── src/
│   ├── catertrax_scraper.py   # Playwright login + invoice parsing
│   ├── bread_mapper.py        # Recipe translation logic
│   ├── ai_mapper.py           # Gemini fallback for unmatched items
│   └── excel_generator.py     # Dynamic pandas Excel builder
├── llm_integration/
│   └── test_ai.py             # Manual test for the AI mapper
├── assets/
│   └── Excel Format.pdf       # Reference layout for the daily sheet
└── output/                    # Generated .xlsx files (created automatically, git-ignored)
```

## 🛠️ How to Use
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Copy `.env.example` to `.env` and fill in your Catertrax credentials and (optionally) a `GEMINI_API_KEY`. Without a Gemini key, the AI fallback is skipped and only rule-based mapping is used.
3. Run from the command line:
   ```bash
   python run_automation.py
   ```
   or launch the web UI:
   ```bash
   streamlit run app.py
   ```
4. Get your spreadsheet from the `output/` folder (or the download button in the web UI).

> **Streamlit Community Cloud:** add `CATERTRAX_URLS`, `CATERTRAX_USERNAME`, `CATERTRAX_PASSWORD` and `GEMINI_API_KEY` as app secrets instead of using a `.env` file.

## 🔧 Future Implementations
- **Email Integration**: The second phase of this project will integrate an email-parsing module to intercept and inject the raw Dining Hall (Eagle, Bruce) orders directly into the matrix before the final Excel sheet is built.
