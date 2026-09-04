from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Union, Optional

URL_ATTRIBUTES = {"href", "src", "action", "data-src", "data-url"}

class RuleExtractor:
    """
    Extracts structured tabular or object data from HTML content using CSS selectors.
    Supports resolving relative URLs (href, src) to absolute URLs when base_url is provided.
    """

    @staticmethod
    def extract_single(
        html_content: str, 
        fields: Dict[str, str], 
        base_url: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Extracts a single dictionary record from HTML using a map of {field_name: css_selector}.
        Example:
            fields = {"title": "h1.product-title", "price": "span.price", "link": "a::attr(href)"}
        """
        if not html_content:
            return {field: None for field in fields}

        soup = BeautifulSoup(html_content, "html.parser")
        result = {}

        for field_name, selector in fields.items():
            if "::attr(" in selector:
                clean_selector, attr_part = selector.split("::attr(", 1)
                attr_name = attr_part.rstrip(")")
                el = soup.select_one(clean_selector) if clean_selector else soup
                if el and el.has_attr(attr_name):
                    val = el.get(attr_name)
                    if val and base_url and attr_name.lower() in URL_ATTRIBUTES:
                        val = urljoin(base_url, str(val))
                    result[field_name] = str(val) if val is not None else None
                else:
                    result[field_name] = None
            else:
                element = soup.select_one(selector)
                result[field_name] = element.get_text(strip=True) if element else None

        return result

    @staticmethod
    def extract_list(
        html_content: str, 
        item_selector: str, 
        fields: Dict[str, str], 
        base_url: Optional[str] = None
    ) -> List[Dict[str, Optional[str]]]:
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
                    clean_sel, attr_part = selector.split("::attr(", 1)
                    attr_name = attr_part.rstrip(")")
                    target_el = item.select_one(clean_sel) if clean_sel else item
                    if target_el and target_el.has_attr(attr_name):
                        val = target_el.get(attr_name)
                        if val and base_url and attr_name.lower() in URL_ATTRIBUTES:
                            val = urljoin(base_url, str(val))
                        record[field_name] = str(val) if val is not None else None
                    else:
                        record[field_name] = None
                else:
                    target_el = item.select_one(selector) if selector else item
                    record[field_name] = target_el.get_text(strip=True) if target_el else None
            results.append(record)

        return results
