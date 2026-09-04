import time
import requests
from typing import Optional, Dict
from urllib.parse import urljoin
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
    robots.txt compliance, manual safe redirect inspection, and automatic content sanitization.
    """
    def __init__(self, rate_limiter: Optional[DomainRateLimiter] = None, timeout: float = 10.0, ignore_robots: bool = False):
        self.rate_limiter = rate_limiter or DomainRateLimiter()
        self.timeout = timeout
        self.ignore_robots = ignore_robots

    def fetch(self, url: str, extra_headers: Optional[Dict[str, str]] = None, max_redirects: int = 5) -> FetchResult:
        headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
        start_time = time.time()
        current_url = url
        redirect_count = 0

        while True:
            # 1. Safety Check: SSRF and Protocol Validation on current URL
            is_safe, reason = validate_url(current_url)
            if not is_safe:
                return FetchResult(
                    url=current_url,
                    status_code=400,
                    success=False,
                    error_message=f"Safety violation: {reason}"
                )

            # 2. Safety Check: Rate Limiting & Robots.txt
            try:
                if not self.ignore_robots:
                    self.rate_limiter.wait_if_needed(current_url)
            except PermissionError as e:
                return FetchResult(
                    url=current_url,
                    status_code=403,
                    success=False,
                    error_message=str(e)
                )

            # 3. Perform request with allow_redirects=False to safely inspect every hop
            try:
                response = requests.get(
                    current_url, 
                    headers=headers, 
                    timeout=self.timeout, 
                    allow_redirects=False
                )
            except requests.RequestException as e:
                elapsed = time.time() - start_time
                return FetchResult(
                    url=current_url,
                    status_code=500,
                    success=False,
                    error_message=f"Request failed: {str(e)}",
                    elapsed_seconds=elapsed
                )

            # 4. Handle redirects safely: validate destination before making the next connection
            if response.is_redirect or response.is_permanent_redirect or response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1
                if redirect_count > max_redirects:
                    elapsed = time.time() - start_time
                    return FetchResult(
                        url=current_url,
                        status_code=400,
                        success=False,
                        error_message=f"Too many redirects (exceeded limit of {max_redirects})",
                        elapsed_seconds=elapsed
                    )

                location = response.headers.get("Location")
                if not location:
                    elapsed = time.time() - start_time
                    return FetchResult(
                        url=current_url,
                        status_code=response.status_code,
                        success=False,
                        error_message="Redirect response missing Location header.",
                        elapsed_seconds=elapsed,
                    )

                current_url = urljoin(current_url, location)
                continue

            # Non-redirect response reached
            break

        elapsed = time.time() - start_time

        if response.status_code == 200:
            raw_html = response.text
            clean_text = HTMLSanitizer.extract_clean_text(raw_html)
            return FetchResult(
                url=current_url,
                status_code=response.status_code,
                success=True,
                raw_html=raw_html,
                clean_text=clean_text,
                elapsed_seconds=elapsed,
                headers=dict(response.headers)
            )
        else:
            return FetchResult(
                url=current_url,
                status_code=response.status_code,
                success=False,
                error_message=f"HTTP {response.status_code}: {response.reason}",
                elapsed_seconds=elapsed,
                headers=dict(response.headers)
            )
