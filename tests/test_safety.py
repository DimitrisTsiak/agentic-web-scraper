import unittest
from src.safety.url_validator import validate_url

class TestURLValidator(unittest.TestCase):
    def test_valid_public_urls(self):
        valid_urls = [
            "https://example.com",
            "http://python.org/downloads",
            "https://news.ycombinator.com",
        ]
        for url in valid_urls:
            is_safe, reason = validate_url(url)
            self.assertTrue(is_safe, f"Expected {url} to be safe, got reason: {reason}")

    def test_ssrf_and_blocked_urls(self):
        blocked_urls = [
            "http://localhost",
            "http://127.0.0.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1",
            "http://192.168.1.1",
            "file:///etc/passwd",
            "ftp://example.com",
            "gopher://example.com",
        ]
        for url in blocked_urls:
            is_safe, reason = validate_url(url)
            self.assertFalse(is_safe, f"Expected {url} to be blocked! Reason returned: {reason}")

if __name__ == "__main__":
    unittest.main()
