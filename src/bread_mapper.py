import json
import math
import os
import sys

try:
    from src.ai_mapper import AIBreadMapper
except ImportError:
    try:
        from ai_mapper import AIBreadMapper
    except ImportError:
        AIBreadMapper = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class BreadMapper:
    def __init__(self, rules_filepath=os.path.join(PROJECT_ROOT, "config", "mapping_rules.json"),
                 menu_filepath=os.path.join(PROJECT_ROOT, "config", "menu_items.json")):
        self.rules_filepath = rules_filepath
        self.menu_filepath = menu_filepath
        self.rules = self._load_json(self.rules_filepath)
        self.menu_mapping = self._load_json(self.menu_filepath)
        self.ai_mapper = None
        if AIBreadMapper:
            try:
                self.ai_mapper = AIBreadMapper(config_path=self.rules_filepath)
            except Exception as e:
                print(f"WARNING: AI mapper unavailable ({e}); continuing with rule-based mapping only.")

    def _load_json(self, filepath):
        if not os.path.exists(filepath):
            return {}
        with open(filepath, "r") as f:
            return json.load(f)

    def find_matching_rule(self, item_name):
        """Finds the mapping rule for the given item name."""
        item_lower = item_name.lower()
        
        # 1. Check if the item matches any menu item in menu_items.json
        bread_type = None
        for menu_item, mapped_bread in self.menu_mapping.items():
            # If the invoice item name contains the menu item name (or vice versa)
            if menu_item.lower() in item_lower or item_lower in menu_item.lower():
                bread_type = mapped_bread
                break
                
        # 2. If not in menu_items, check if the item name ITSELF is a bread type
        if not bread_type:
            bread_type = item_name
            
        # 3. Now look up the bread_type in mapping_rules.json
        bread_lower = bread_type.lower()
        
        # Exact match first
        for key in self.rules:
            if key.lower() == bread_lower:
                return bread_type, key, self.rules[key]
                
        # Partial match (handle hyphens and punctuation)
        clean_bread_lower = bread_lower.replace('-', ' ')
        for key in self.rules:
            key_lower = key.lower()
            if key_lower in clean_bread_lower or key_lower.rstrip('s') in clean_bread_lower:
                return bread_type, key, self.rules[key]
                
        return bread_type, None, None

    def calculate_bread_needs(self, item_name, qty, site_name=None):
        """
        Takes an item name and its ordered quantity, applies the mapping rule,
        and returns a dict with the preparation details.
        """
        item_lower = item_name.lower()
        
        # --- NEW DYNAMIC RULES ---
        # 1. Sandwiches (Always 14mm White Bread, 2 slices per sandwich)
        if "sandwich" in item_lower:
            bread_qty = math.ceil((qty * 2) / 20)
            return {
                "item_name": item_name,
                "requested_qty": qty,
                "bread_needed": "White Bread - 14mm",
                "bread_qty": bread_qty,
                "bread_unit": "loaf",
                "notes": "2 slices per sandwich (20 slices per loaf)"
            }
            
        # 2. French Toast (23mm slices, dynamically extract bread type)
        if "french toast" in item_lower:
            bread_type = "Sourdough" # Default fallback
            if "white bread" in item_lower:
                bread_type = "White Bread"
            elif "brioche" in item_lower:
                bread_type = "Brioche"
            elif "challah" in item_lower:
                bread_type = "Challah"
            elif "wheat" in item_lower:
                bread_type = "Whole Wheat Bread"
                
            bread_qty = math.ceil(qty / 10)
            return {
                "item_name": item_name,
                "requested_qty": qty,
                "bread_needed": f"{bread_type} - 23mm",
                "bread_qty": bread_qty,
                "bread_unit": "loaf",
                "notes": "1 slice per person (10 slices per 23mm loaf)"
            }
        # -------------------------
        
        bread_type, matched_key, rule = self.find_matching_rule(item_name)
        
        # 3. AI Fallback (ONLY if standard matching failed)
        if not rule:
            if hasattr(self, 'ai_mapper') and self.ai_mapper:
                ai_result = self.ai_mapper.map_item(item_name)
                if ai_result.get("matched_bread") != "None" and ai_result.get("confidence", 0) >= 75:
                    ai_bread_key = ai_result["matched_bread"]
                    ai_rule = self.rules.get(ai_bread_key)
                    if ai_rule:
                        try:
                            # Evaluate math
                            safe_env = {"math": math, "qty": qty}
                            calculation_formula = ai_rule.get("calculate")
                            raw_items = math.ceil(eval(calculation_formula, {"__builtins__": None}, safe_env))
                            
                            # Determine unit handling
                            bin_size = ai_rule.get("bin_size")
                            bread_unit = ai_rule.get("unit", "unknown")
                            
                            if bin_size and site_name != "untfoodtogo":
                                if raw_items < bin_size:
                                    bread_qty = raw_items
                                    bread_unit = "ct"
                                else:
                                    bread_qty = math.ceil(raw_items / bin_size)
                            else:
                                bread_qty = raw_items
                                
                            return {
                                "item_name": item_name,
                                "requested_qty": qty,
                                "bread_needed": ai_bread_key,
                                "bread_qty": bread_qty,
                                "bread_unit": bread_unit,
                                "notes": f"[AI Fallback - {ai_result['confidence']}%] {ai_result['notes']}"
                            }
                        except Exception as e:
                            print(f"Warning: AI successfully mapped to {ai_bread_key} but calculation failed: {e}")
            return None # No mapping rule found for this item
            
        calculation_formula = rule.get("calculate")
        bin_size = rule.get("bin_size")
        
        bread_unit = rule.get("unit")
        
        # Site-specific logic for bin sizes
        if bin_size:
            if site_name == "untfoodtogo":
                # For untfoodtogo (retail), qty is already the number of bins
                bread_qty = qty
            else:
                try:
                    safe_env = {"math": math, "qty": qty}
                    raw_items = math.ceil(eval(calculation_formula, {"__builtins__": None}, safe_env))
                    if raw_items < bin_size:
                        bread_qty = raw_items
                        bread_unit = "ct"
                    else:
                        bread_qty = math.ceil(raw_items / bin_size)
                except Exception as e:
                    print(f"Error calculating bread for {item_name}: {e}")
                    bread_qty = qty
        else:
            # Safely evaluate the formula for normal items (or bagel chips/crackers where calculate="qty")
            try:
                safe_env = {"math": math, "qty": qty}
                bread_qty = eval(calculation_formula, {"__builtins__": None}, safe_env)
            except Exception as e:
                print(f"Error calculating bread for {item_name}: {e}")
                bread_qty = qty
            
        return {
            "item_name": item_name,
            "requested_qty": qty,
            "bread_needed": matched_key,
            "bread_qty": bread_qty,
            "bread_unit": bread_unit,
            "notes": rule.get("note", "")
        }

if __name__ == "__main__":
    # Simple test
    mapper = BreadMapper()
    print(mapper.calculate_bread_needs("Clark Bakery Hoagie", 14))
    print(mapper.calculate_bread_needs("Assorted Bread (Crowd Pleaser)", 50))
