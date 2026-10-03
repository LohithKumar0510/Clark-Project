import os
import json
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_RULES_PATH = os.path.join(PROJECT_ROOT, "config", "mapping_rules.json")

# Load environment variables (like GEMINI_API_KEY) from the project root,
# regardless of the current working directory.
load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

class MappingResult(BaseModel):
    matched_bread: str = Field(description="The exact bread key from the known list, or 'None' if no match.")
    confidence: int = Field(description="Confidence score from 0 to 100")
    notes: str = Field(description="Brief explanation of why this bread was chosen")

class AIBreadMapper:
    def __init__(self, config_path=DEFAULT_RULES_PATH):
        # Fall back to the project's config if the given path doesn't exist
        if not os.path.exists(config_path):
            config_path = DEFAULT_RULES_PATH
            
        # Load bread keys
        try:
            with open(config_path, "r") as f:
                self.rules = json.load(f)
            self.bread_keys = list(self.rules.keys())
        except Exception as e:
            print(f"Error loading rules from {config_path}: {e}")
            self.bread_keys = []
            
        # Initialize Gemini Client
        # Automatically picks up GEMINI_API_KEY from .env
        # Without a key, genai.Client() raises, so AI fallback is disabled instead
        # of crashing the whole automation.
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if not api_key:
            print("WARNING: GEMINI_API_KEY not set - AI fallback mapping disabled.")
        else:
            self.client = genai.Client(api_key=api_key)
        
        # Build System Prompt
        self.system_prompt = f"""
You are an expert culinary data parser for a bakery.
Your job is to read messy catering invoice items and map them to the exact bread required from our known list.

Here is the strict list of known breads:
{json.dumps(self.bread_keys, indent=2)}

Rules:
1. Return ONLY the exact name of the bread from the known list in the 'matched_bread' field.
2. If you are less than 75% confident that the item requires one of these breads, return "None" in the 'matched_bread' field.
3. Ignore drinks, standard hot food, or non-bread items entirely.
4. Add a brief explanation in 'notes'.
"""

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_gemini(self, item_description: str):
        return self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=item_description,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MappingResult,
                system_instruction=self.system_prompt,
                temperature=0.0
            )
        )

    def map_item(self, item_description: str) -> dict:
        if self.client is None:
            return {"matched_bread": "None", "confidence": 0, "notes": "AI mapping disabled (no GEMINI_API_KEY)"}
        try:
            response = self._call_gemini(item_description)

            
            # Parse the strict JSON response
            result = MappingResult.model_validate_json(response.text)
            return result.model_dump()
            
        except Exception as e:
            print(f"AI Mapping failed: {e}")
            return {"matched_bread": "None", "confidence": 0, "notes": str(e)}

if __name__ == "__main__":
    print("Testing AI Mapper...")
    mapper = AIBreadMapper()
    print("Available keys loaded:", len(mapper.bread_keys))
