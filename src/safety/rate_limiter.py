import time
import threading
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from typing import Dict, Tuple, Optional

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
                rfp = RobotFileParser()
                rfp.set_url(robots_url)
                try:
                    rfp.read()
                except Exception:
                    # If robots.txt cannot be fetched or parsed, default to permissive but cautious
                    pass
                self._robot_parsers[domain] = rfp

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
