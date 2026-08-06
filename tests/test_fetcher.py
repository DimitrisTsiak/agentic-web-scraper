import unittest
from unittest.mock import patch, MagicMock
from src.fetcher.static_fetcher import StaticFetcher

class TestStaticFetcher(unittest.TestCase):
    def test_ssrf_blocked_fetch(self):
        fetcher = StaticFetcher()
        result = fetcher.fetch("http://127.0.0.1/admin")
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 400)
        self.assertIn("Safety violation", result.error_message)

    @patch("requests.get")
    def test_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Scraped Header</h1><script>bad</script></body></html>"
        mock_response.url = "https://example.com"
        mock_response.history = []
        mock_response.headers = {"Content-Type": "text/html"}
        mock_get.return_value = mock_response

        fetcher = StaticFetcher()
        # Mock rate limiter to avoid network calls to robots.txt during tests
        fetcher.rate_limiter.wait_if_needed = MagicMock()

        result = fetcher.fetch("https://example.com")
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertIn("Scraped Header", result.clean_text)
        self.assertNotIn("bad", result.clean_text)

if __name__ == "__main__":
    unittest.main()
