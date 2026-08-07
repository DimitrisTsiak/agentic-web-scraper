from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from src.fetcher.static_fetcher import StaticFetcher
from src.extractor.ai_extractor import AIExtractor

class MultiPageCrawler:
    """
    Multi-page crawler that navigates pagination links and collects aggregated
    data across multiple web pages using AI extraction.
    """

    def __init__(self, fetcher: Optional[StaticFetcher] = None, ai_extractor: Optional[AIExtractor] = None):
        self.fetcher = fetcher or StaticFetcher()
        self.ai_extractor = ai_extractor or AIExtractor()

    def _find_next_page_url(self, current_url: str, html_content: str) -> Optional[str]:
        """
        Detects the 'Next' page link using standard rel='next' attributes,
        common class names, or link text ('Next', 'Next >', '>>').
        """
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Look for rel="next"
        next_tag = soup.find("a", attrs={"rel": "next"})
        if next_tag and next_tag.get("href"):
            return urljoin(current_url, next_tag["href"])

        # 2. Look for common 'next' class names or IDs
        for a_tag in soup.find_all("a", href=True):
            class_and_id = " ".join(a_tag.get("class", [])) + " " + a_tag.get("id", "")
            text = a_tag.get_text(strip=True).lower()

            if any(k in class_and_id.lower() for k in ["next", "pagination-next", "pager-next"]):
                return urljoin(current_url, a_tag["href"])

            if text in ["next", "next >", "next »", ">>", "επόμενη"]:
                return urljoin(current_url, a_tag["href"])

        return None

    def crawl_and_extract(
        self, start_url: str, prompt: str, max_pages: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Crawls up to max_pages starting from start_url, extracting structured items on each page.
        Returns a single combined list of extracted records.
        """
        all_records: List[Dict[str, Any]] = []
        current_url: Optional[str] = start_url
        visited_urls = set()
        page_count = 0

        while current_url and page_count < max_pages and current_url not in visited_urls:
            visited_urls.add(current_url)
            page_count += 1
            print(f"[CRAWLER] Processing page {page_count}/{max_pages}: {current_url}")

            fetch_result = self.fetcher.fetch(current_url)
            if not fetch_result.success:
                print(f"[CRAWLER ERROR] Failed to fetch {current_url}: {fetch_result.error_message}")
                break

            # Extract data from current page using AI
            try:
                page_data = self.ai_extractor.extract(fetch_result.clean_text, prompt)
                if isinstance(page_data, list):
                    all_records.extend(page_data)
                elif isinstance(page_data, dict):
                    all_records.append(page_data)
            except Exception as e:
                print(f"[CRAWLER ERROR] Extraction failed on page {page_count}: {str(e)}")

            # Find next page URL
            current_url = self._find_next_page_url(current_url, fetch_result.raw_html)
            if not current_url:
                print("[CRAWLER] No further pagination links found.")
                break

        return all_records
