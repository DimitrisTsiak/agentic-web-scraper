import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

QA_SYSTEM_PROMPT = """You are an intelligent Web Page Q&A Assistant for a Web Scraper Agent.
Your goal is to answer the user's question accurately and helpfully using ONLY the provided webpage content.

RULES:
1. Base your answer on the webpage content provided below. Use you internal knowledge to provide additional information regarding the web page contents, but make sure to explicitly state that the information is not from the webpage content.
2. If the user asks for recommendations or specific items (e.g., "are there any must have CS books available?"), list relevant items found on the page with any details (like price, rating, or description) available.
3. If the answer cannot be found in the provided webpage content, state clearly that the information is not available on the page.
4. Keep your answer clear, well-formatted, and concise.
"""

class AIQAEngine:
    """
    Q&A Engine using Google Gen AI SDK (genai.Client) to answer natural language questions
    grounded directly in extracted web page content.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_GEMINI_MODEL):
        self._override_key = api_key
        self.model = model

    def __repr__(self) -> str:
        return f"<AIQAEngine model='{self.model}'>"

    def _get_api_key(self) -> str:
        key = self._override_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key or key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please add your Gemini API key to the .env file."
            )
        return key

    def answer_question(self, clean_text: str, question: str, max_text_length: int = 15000) -> Dict[str, Any]:
        """
        Answers a user question based on webpage text using the Google Gen AI SDK.
        Returns a dict containing 'answer', 'model', and 'content_length'.
        """
        key = self._get_api_key()

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

        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                )
            )

            answer_text = (response.text or "").strip()

            return {
                "answer": answer_text,
                "model": self.model,
                "content_length": len(truncated_text)
            }

        except Exception as e:
            raise RuntimeError(f"Q&A Engine failed: {str(e)}")
