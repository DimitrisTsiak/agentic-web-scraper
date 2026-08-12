import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

QA_SYSTEM_PROMPT = """You are an intelligent Web Page Q&A Assistant for a Web Scraper Agent.
Your goal is to answer the user's question accurately and helpfully using ONLY the provided webpage content.

RULES:
1. Base your answer strictly on the webpage content provided below.
2. If the user asks for recommendations or specific items (e.g., "are there any must have CS books available?"), list relevant items found on the page with any details (like price, rating, or description) available.
3. If the answer cannot be found in the provided webpage content, state clearly that the information is not available on the page.
4. Keep your answer clear, well-formatted, and concise.
"""

class AIQAEngine:
    """
    Q&A Engine using Google Gemini API to answer natural language questions
    grounded directly in extracted web page content.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    def _check_api_key(self):
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please add your Gemini API key to the .env file."
            )

    def answer_question(self, clean_text: str, question: str, max_text_length: int = 15000) -> Dict[str, Any]:
        """
        Answers a user question based on webpage text.
        Returns a dict containing 'answer', 'model', and 'content_length'.
        """
        self._check_api_key()

        if not clean_text or not clean_text.strip():
            return {
                "answer": "No content was extracted from the target web page.",
                "model": self.model,
                "content_length": 0
            }

        truncated_text = clean_text[:max_text_length]
        prompt = (
            f"{QA_SYSTEM_PROMPT}\n\n"
            f"WEBPAGE CONTENT:\n{truncated_text}\n\n"
            f"USER QUESTION:\n{question}"
        )

        url = f"{GEMINI_API_ENDPOINT.format(model=self.model)}?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
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

            answer_text = parts[0].get("text", "").strip()

            return {
                "answer": answer_text,
                "model": self.model,
                "content_length": len(truncated_text)
            }

        except Exception as e:
            raise RuntimeError(f"Q&A Engine failed: {str(e)}")
