import re
from bs4 import BeautifulSoup
from typing import Optional

# Tags that should be completely removed (including their internal content)
DANGEROUS_TAGS = [
    "script", "style", "iframe", "object", "embed", "applet",
    "noscript", "form", "svg", "canvas", "meta", "link"
]

# Attributes that should be stripped from all remaining tags
DANGEROUS_ATTRIBUTES = [
    r"^on\w+",           # Event handlers like onclick, onload, onerror
    r"^javascript:",     # JS protocol targets
    r"^data:",           # Data URI targets
]

# Pattern for hidden unicode / zero-width space characters
INVISIBLE_CHARS_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u0000-\u0008\u000B\u000C\u000E-\u001F]")

# Regex pattern for basic credit card masking (PII)
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

class HTMLSanitizer:
    """
    Sanitizes raw HTML content to protect against Prompt Injection,
    XSS payloads, and malformed/malicious web elements.
    """

    @staticmethod
    def sanitize_html(html_content: str, remove_images: bool = False) -> str:
        """
        Removes scripts, styles, dangerous tags, inline event handlers,
        and returns clean HTML text.
        """
        if not html_content or not isinstance(html_content, str):
            return ""

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove dangerous tags along with their contents
        tags_to_remove = DANGEROUS_TAGS + (["img"] if remove_images else [])
        for tag in soup.find_all(tags_to_remove):
            tag.decompose()

        # 2. Strip dangerous inline attributes from remaining tags
        for tag in soup.find_all(True):
            attrs_to_remove = []
            for attr in tag.attrs:
                val = str(tag.attrs[attr])
                for pattern in DANGEROUS_ATTRIBUTES:
                    if re.match(pattern, attr, re.IGNORECASE) or re.match(pattern, val, re.IGNORECASE):
                        attrs_to_remove.append(attr)
                        break

            for attr in attrs_to_remove:
                del tag.attrs[attr]

        return str(soup)

    @staticmethod
    def extract_clean_text(html_content: str, max_length: Optional[int] = 100000) -> str:
        """
        Extracts clean human-readable text from HTML, stripping all tags,
        invisible characters, and excessive whitespace.
        """
        cleaned_html = HTMLSanitizer.sanitize_html(html_content)
        soup = BeautifulSoup(cleaned_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        # Strip invisible characters
        text = INVISIBLE_CHARS_PATTERN.sub("", text)

        # Normalize multiple spaces and newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", "\n", text).strip()

        if max_length and len(text) > max_length:
            text = text[:max_length] + "... [TRUNCATED]"

        return text

    @staticmethod
    def redact_pii(text: str) -> str:
        """
        Redacts basic sensitive PII patterns like credit card numbers.
        """
        return CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", text)
