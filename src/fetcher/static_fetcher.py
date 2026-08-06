import time
import requests
from typing import Optional, Dict
from src.safety.url_validator import validate_url
from src.safety.rate_limiter import DomainRateLimiter
from src.safety.sanitizer import HTMLSanitizer
from .models import FetchResult

DEFAULT_HEADERS = {
    "User-Agent": "WebScraperAgent/1.0 (+https://github.com/web-scraper-agent)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

class StaticFetcher:
    """
    Lightweight, fast HTTP fetcher with integrated safety checks,
    robots.txt compliance, and automatic content sanitization.
    """
    def __init__(self, rate_limiter: Optional[DomainRateLimiter] = None, timeout: float = 10.0):
        self.rate_limiter = rate_limiter or DomainRateLimiter()
        self.timeout = timeout

    def fetch(self, url: str, extra_headers: Optional[Dict[str, str]] = None) -> FetchResult:
        # 1. Safety Check: SSRF and Protocol Validation
        is_safe, reason = validate_url(url)
        if not is_safe:
            return FetchResult(
                url=url,
                status_code=400,
                success=False,
                error_message=f"Safety violation: {reason}"
            )

        # 2. Safety Check: Rate Limiting & Robots.txt
        try:
            self.rate_limiter.wait_if_needed(url)
        except PermissionError as e:
            return FetchResult(
                url=url,
                status_code=403,
                success=False,
                error_message=str(e)
            )

        headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
        start_time = time.time()

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            elapsed = time.time() - start_time

            # 3. Safety Check: Final destination URL check if redirected
            if response.history:
                final_is_safe, final_reason = validate_url(response.url)
                if not final_is_safe:
                    return FetchResult(
                        url=response.url,
                        status_code=400,
                        success=False,
                        error_message=f"Redirect safety violation: {final_reason}"
                    )

            if response.status_code == 200:
                raw_html = response.text
                clean_text = HTMLSanitizer.extract_clean_text(raw_html)
                return FetchResult(
                    url=response.url,
                    status_code=response.status_code,
                    success=True,
                    raw_html=raw_html,
                    clean_text=clean_text,
                    elapsed_seconds=elapsed,
                    headers=dict(response.headers)
                )
            else:
                return FetchResult(
                    url=response.url,
                    status_code=response.status_code,
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.reason}",
                    elapsed_seconds=elapsed,
                    headers=dict(response.headers)
                )

        except requests.RequestException as e:
            elapsed = time.time() - start_time
            return FetchResult(
                url=url,
                status_code=500,
                success=False,
                error_message=f"Request failed: {str(e)}",
                elapsed_seconds=elapsed
            )
