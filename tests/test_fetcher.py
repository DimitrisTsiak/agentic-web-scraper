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

    @patch("requests.get")
    def test_redirect_to_ssrf_blocked(self, mock_get):
        redirect_response = MagicMock()
        redirect_response.status_code = 302
        redirect_response.is_redirect = True
        redirect_response.is_permanent_redirect = False
        redirect_response.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
        mock_get.return_value = redirect_response

        fetcher = StaticFetcher()
        fetcher.rate_limiter.wait_if_needed = MagicMock()

        result = fetcher.fetch("https://example.com/redirect")
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 400)
        self.assertIn("Safety violation", result.error_message)
        self.assertIn("169.254.169.254", result.error_message)

    @patch("requests.get")
    def test_safe_redirect_followed(self, mock_get):
        redirect_resp = MagicMock()
        redirect_resp.status_code = 301
        redirect_resp.is_redirect = True
        redirect_resp.is_permanent_redirect = True
        redirect_resp.headers = {"Location": "/final-page"}

        final_resp = MagicMock()
        final_resp.status_code = 200
        final_resp.is_redirect = False
        final_resp.is_permanent_redirect = False
        final_resp.text = "<html><body>Final Content</body></html>"
        final_resp.headers = {"Content-Type": "text/html"}

        mock_get.side_effect = [redirect_resp, final_resp]

        fetcher = StaticFetcher()
        fetcher.rate_limiter.wait_if_needed = MagicMock()

        result = fetcher.fetch("https://example.com/start")
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertIn("Final Content", result.clean_text)
        self.assertEqual(result.url, "https://example.com/final-page")

if __name__ == "__main__":
    unittest.main()
