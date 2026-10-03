import pandas as pd
import os
from datetime import datetime

ROWS = [
    "Autumn flatbread",
    "Avesta rolls",
    "Bagel chips",
    "Challah buns, 42 ct",
    "Cheddar Cracker",
    "Ciabatta, 3x6",
    "Croissant, 5 oz",
    "Dinner rolls, 40 gm",
    "Focaccia sheet",
    "Garlic bread sticks",
    "Hoagie, 36, 120g",
    "Hot dog bun, 72",
    "Jr Sem Burger 72",
    "Kolache dough,",
    "MG Sourdough",
    "Naan, 60g",
    "Pita Bread, 80g",
    "Semolina bun",
    "Silver Dollar 30g",
    "Sourdough loaf, 2#",
    "Tortilla dough 1 oz",
    "Union Pizza 8 oz.",
    "Union Pizza 16 oz.",
    "Union Pizza 24 oz",
    "Vegan Rolls",
    "Wheat Hoagie",
    "Wheat Loaf",
    "White Loaf",
    "Baguette",
    "Bao Buns"
]

BREAD_TO_ROW = {
    "Autumn Flatbread": "Autumn flatbread",
    "Avesta Rolls": "Avesta rolls",
    "Bagel chips": "Bagel chips",
    "Challah Buns": "Challah buns, 42 ct",
    "Cheddar Crackers": "Cheddar Cracker",
    "Ciabatta": "Ciabatta, 3x6",
    "Croissant": "Croissant, 5 oz",
    "Dinner Rolls": "Dinner rolls, 40 gm",
    "Focaccia": "Focaccia sheet",
    "Garlic bread sticks": "Garlic bread sticks",
    "Hoagies": "Hoagie, 36, 120g",
    "Hot dog bun": "Hot dog bun, 72",
    "Jr. Sem Burger": "Jr Sem Burger 72",
    "Kolache dough": "Kolache dough,",
    "MG Sourdough": "MG Sourdough",
    "Naan": "Naan, 60g",
    "Pita bread": "Pita Bread, 80g",
    "Semolina Bun": "Semolina bun",
    "Silver Dollar": "Silver Dollar 30g",
    "Sourdough Loaf": "Sourdough loaf, 2#",
    "Tortilla": "Tortilla dough 1 oz",
    "Union Pizza 8 oz": "Union Pizza 8 oz.",
    "Union Pizza 16 oz": "Union Pizza 16 oz.",
    "Union Pizza 24 Oz": "Union Pizza 24 oz",
    "Vegan Rolls": "Vegan Rolls",
    "Wheat Hoagie": "Wheat Hoagie",
    "Wheat Loaf": "Wheat Loaf",
    "White Loaf": "White Loaf",
    "Sourdough Baguette": "Baguette",
    "Bao Buns": "Bao Buns"
}

class SpreadsheetManager:
    def __init__(self, base_filename="preparation_list"):
        now = datetime.now()
        day_of_week = now.strftime("%A")
        date_str = now.strftime("%Y-%m-%d")
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        os.makedirs(output_dir, exist_ok=True)
        self.filepath = os.path.join(output_dir, f"{base_filename}_{day_of_week}_{date_str}.xlsx")
        self.base_columns = ["ITEM", "TOTALS"]
        
        self._initialize_spreadsheet()

    def _initialize_spreadsheet(self):
        if not os.path.exists(self.filepath):
            # Start empty with just ITEM and TOTALS
            df = pd.DataFrame(columns=self.base_columns)
            df.to_excel(self.filepath, index=False)

    def append_order_preparations(self, site_name, location, order_id, order_date, preparations):
        """
        Dynamically routes orders to the correct column based on location.
        """
        if not preparations:
            return

        if not os.path.exists(self.filepath):
            self._initialize_spreadsheet()

        df = pd.read_excel(self.filepath)
        
        # Determine Target Column
        target_col = "CATERING"
        if site_name == "untfoodtogo":
            loc_upper = location.upper() if location else ""
            if "VERDE" in loc_upper:
                target_col = "VED"
            elif "UNION KITCHEN" in loc_upper:
                target_col = "UNION"
            elif "UNION BURGER" in loc_upper:
                target_col = "U Burger"
            elif "EAGLE" in loc_upper:
                target_col = "Eagle"
            elif "BRUCE" in loc_upper:
                target_col = "BRUCE"
            elif "AVESTA" in loc_upper:
                target_col = "AVESTA"
            elif "FOODCOURT" in loc_upper:
                target_col = "FOODCOURT"
            else:
                target_col = "RETAIL" # Fallback if unknown

        # Create column if it doesn't exist
        if target_col not in df.columns:
            # Insert before TOTALS
            totals_idx = df.columns.get_loc("TOTALS")
            df.insert(totals_idx, target_col, 0)

        for prep in preparations:
            bread_needed = prep.get("bread_needed")
            bread_qty = prep.get("bread_qty")
            
            row_item = BREAD_TO_ROW.get(bread_needed, bread_needed)
            if not row_item:
                continue
                
            row_idx = df.index[df['ITEM'] == row_item].tolist()
            if row_idx:
                idx = row_idx[0]
            else:
                idx = len(df)
                df.loc[idx, "ITEM"] = row_item
                for col in df.columns:
                    if col != "ITEM":
                        df.at[idx, col] = 0
            
            current_val = df.at[idx, target_col]
            if pd.isna(current_val) or not isinstance(current_val, (int, float)):
                current_val = 0
            df.at[idx, target_col] = current_val + bread_qty

        # Re-calculate TOTALS
        numeric_cols = [c for c in df.columns if c not in ["ITEM", "TOTALS"]]
        df["TOTALS"] = df[numeric_cols].sum(axis=1)

        df.to_excel(self.filepath, index=False)
        print(f"Successfully routed {len(preparations)} items to '{target_col}' for Order #{order_id}")
