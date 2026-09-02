import time
import threading
import requests
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Dict, Tuple, Optional
from src.safety.url_validator import validate_url

DEFAULT_USER_AGENT = "WebScraperAgent/1.0 (+https://github.com/web-scraper-agent)"
DEFAULT_MIN_DELAY_SECONDS = 1.0

class DomainRateLimiter:
    """
    Manages per-domain rate limiting and robots.txt compliance to ensure polite crawling.
    """
    def __init__(self, default_delay: float = DEFAULT_MIN_DELAY_SECONDS, user_agent: str = DEFAULT_USER_AGENT):
        self.default_delay = default_delay
        self.user_agent = user_agent
        self._last_request_times: Dict[str, float] = {}
        self._robot_parsers: Dict[str, RobotFileParser] = {}
        self._lock = threading.Lock()

    def get_domain(self, url: str) -> str:
        """Extract domain/netloc from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def _fetch_and_parse_robots(self, robots_url: str, timeout: float = 3.0) -> RobotFileParser:
        """
        Safely fetches and parses robots.txt with SSRF validation and redirect inspection.
        Never calls unvalidated urllib.request.urlopen.
        """
        rfp = RobotFileParser()
        rfp.set_url(robots_url)

        is_safe, _ = validate_url(robots_url)
        if not is_safe:
            rfp.parse(["User-agent: *", "Disallow: /"])
            return rfp

        current_url = robots_url
        headers = {"User-Agent": self.user_agent}

        try:
            for _ in range(3):
                is_safe, _ = validate_url(current_url)
                if not is_safe:
                    rfp.parse(["User-agent: *", "Disallow: /"])
                    return rfp

                resp = requests.get(current_url, headers=headers, timeout=timeout, allow_redirects=False)

                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location")
                    if not loc:
                        break
                    current_url = urljoin(current_url, loc)
                    continue

                if resp.status_code == 200:
                    rfp.parse(resp.text.splitlines())
                elif resp.status_code in (401, 403):
                    rfp.parse(["User-agent: *", "Disallow: /"])
                elif resp.status_code == 404:
                    rfp.parse([])
                break

        except Exception:
            rfp.parse([])

        return rfp

    def is_allowed_by_robots(self, url: str, fetch_timeout: float = 3.0) -> Tuple[bool, Optional[float]]:
        """
        Check if the URL is allowed by robots.txt and get any crawl-delay directive.
        Returns (is_allowed: bool, crawl_delay: Optional[float]).
        """
        domain = self.get_domain(url)
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        with self._lock:
            if domain not in self._robot_parsers:
                self._robot_parsers[domain] = self._fetch_and_parse_robots(robots_url, timeout=fetch_timeout)

            rfp = self._robot_parsers[domain]

        allowed = rfp.can_fetch(self.user_agent, url)
        try:
            crawl_delay = rfp.crawl_delay(self.user_agent)
        except Exception:
            crawl_delay = None

        return allowed, crawl_delay

    def wait_if_needed(self, url: str):
        """
        Enforces rate limiting by sleeping if the time since the last request to the domain
        is less than the minimum required delay.
        """
        domain = self.get_domain(url)
        allowed, crawl_delay = self.is_allowed_by_robots(url)

        if not allowed:
            raise PermissionError(f"Access to '{url}' is restricted by site robots.txt policy.")

        required_delay = crawl_delay if crawl_delay is not None else self.default_delay

        with self._lock:
            now = time.time()
            last_time = self._last_request_times.get(domain, 0.0)
            elapsed = now - last_time

            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                time.sleep(sleep_time)

            self._last_request_times[domain] = time.time()
