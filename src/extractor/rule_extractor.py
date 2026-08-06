from bs4 import BeautifulSoup
from typing import List, Dict, Any, Union, Optional

class RuleExtractor:
    """
    Extracts structured tabular or object data from HTML content using CSS selectors.
    """

    @staticmethod
    def extract_single(html_content: str, fields: Dict[str, str]) -> Dict[str, Optional[str]]:
        """
        Extracts a single dictionary record from HTML using a map of {field_name: css_selector}.
        Example:
            fields = {"title": "h1.product-title", "price": "span.price"}
        """
        if not html_content:
            return {field: None for field in fields}

        soup = BeautifulSoup(html_content, "html.parser")
        result = {}

        for field_name, selector in fields.items():
            element = soup.select_one(selector)
            if element:
                # If element has href/src attribute and user asks for it, or get text
                if selector.endswith("::attr(href)") or selector.endswith("::attr(src)"):
                    attr_name = selector.split("::attr(")[1].rstrip(")")
                    clean_selector = selector.split("::attr(")[0]
                    el = soup.select_one(clean_selector)
                    result[field_name] = el.get(attr_name) if el else None
                else:
                    result[field_name] = element.get_text(strip=True)
            else:
                result[field_name] = None

        return result

    @staticmethod
    def extract_list(html_content: str, item_selector: str, fields: Dict[str, str]) -> List[Dict[str, Optional[str]]]:
        """
        Extracts a list of repeated records from container items.
        Example:
            item_selector = ".product-card"
            fields = {"name": ".title", "price": ".price", "link": "a::attr(href)"}
        """
        if not html_content or not item_selector:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        items = soup.select(item_selector)
        results = []

        for item in items:
            record = {}
            for field_name, selector in fields.items():
                if "::attr(" in selector:
                    clean_sel, attr_part = selector.split("::attr(")
                    attr_name = attr_part.rstrip(")")
                    target_el = item.select_one(clean_sel) if clean_sel else item
                    record[field_name] = target_el.get(attr_name) if target_el and target_el.has_attr(attr_name) else None
                else:
                    target_el = item.select_one(selector) if selector else item
                    record[field_name] = target_el.get_text(strip=True) if target_el else None
            results.append(record)

        return results
