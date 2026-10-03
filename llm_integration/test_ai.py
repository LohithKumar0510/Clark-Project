import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ai_mapper import AIBreadMapper

def test_mapper():
    mapper = AIBreadMapper()
    
    # Simulating messy invoice item descriptions
    messy_strings = [
        "Farm Fresh Scrambled Eggs, Home-Style Breakfast Potatoes, Ketchup, Salsa, Filtered water, Coffee / Decaffeinated Coffee / Hot Tea Service",
        "Avessta Rollls (Vegan)",
        "Summer Breakfast Menu with Sourdough French Toast",
        "Giant Submarine Hoagie sandwich with turkey and cheese",
        "Orange Juice, 1 Gallon"
    ]
    
    print("--- Starting AI Mapping Test ---\n")
    for s in messy_strings:
        print(f"Original Text: '{s}'")
        result = mapper.map_item(s)
        print(f"AI Mapping: {result['matched_bread']} (Confidence: {result['confidence']}%)")
        print(f"AI Notes: {result['notes']}\n")

if __name__ == "__main__":
    test_mapper()
