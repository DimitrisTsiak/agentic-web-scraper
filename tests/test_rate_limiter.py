import unittest
import time
from src.safety.rate_limiter import DomainRateLimiter

class TestRateLimiter(unittest.TestCase):
    def test_domain_extraction(self):
        limiter = DomainRateLimiter()
        self.assertEqual(limiter.get_domain("https://news.ycombinator.com/item?id=123"), "news.ycombinator.com")
        self.assertEqual(limiter.get_domain("http://example.com:8080/path"), "example.com:8080")

    def test_rate_limiting_delay(self):
        limiter = DomainRateLimiter(default_delay=0.3)
        url = "https://example.com/test"

        # Mock robots.txt check to avoid network dependency in unit test
        limiter.is_allowed_by_robots = lambda u: (True, None)

        start_time = time.time()
        limiter.wait_if_needed(url)
        limiter.wait_if_needed(url)
        elapsed = time.time() - start_time

        # Second request should take at least 0.3 seconds
        self.assertGreaterEqual(elapsed, 0.28)

if __name__ == "__main__":
    unittest.main()
