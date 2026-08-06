import os
import json
import re
import requests
from typing import List, Dict, Any, Union, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """
You are an expert AI Data Extractor for a Web Scraper Agent.
Your task is to parse text extracted from a web page and extract structured data matching the user's goal.

RULES:
1. Output MUST be valid JSON (either a list of objects or a single JSON object).
2. Do NOT wrap output in markdown code fences or include conversational text.
3. Set missing or unidentifiable values to null.
4. Ensure all extracted strings are clean and trimmed.
"""

class AIExtractor:
    """
    AI-Powered Extractor using Google Gemini API to parse web page content
    and extract structured JSON based on natural language prompt instructions.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    def _check_api_key(self):
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please add your Gemini API key to the .env file."
            )

    def extract(self, clean_text: str, instruction: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extracts structured data from clean webpage text using Google Gemini API.
        """
        self._check_api_key()

        url = f"{GEMINI_API_ENDPOINT.format(model=self.model)}?key={self.api_key}"
        prompt_text = f"{SYSTEM_PROMPT}\n\nUSER EXTRACTION GOAL: {instruction}\n\nWEBPAGE CONTENT:\n{clean_text[:15000]}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {response.text}")

            res_json = response.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini API returned an empty response.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("No content parts returned from Gemini API.")

            raw_text = parts[0].get("text", "").strip()

            # Clean any leftover markdown blocks if present
            clean_json_str = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
            clean_json_str = re.sub(r"```$", "", clean_json_str, flags=re.MULTILINE).strip()

            return json.loads(clean_json_str)

        except Exception as e:
            raise RuntimeError(f"Gemini AI Extraction failed: {str(e)}")
