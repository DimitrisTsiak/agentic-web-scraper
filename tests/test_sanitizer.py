import unittest
from src.safety.sanitizer import HTMLSanitizer

class TestSanitizer(unittest.TestCase):
    def test_script_and_iframe_removal(self):
        dirty_html = """
        <html>
            <head><script>alert('malicious')</script></head>
            <body>
                <h1>Title</h1>
                <iframe src="http://malicious.com"></iframe>
                <p onclick="alert('click')">Safe content</p>
                <style>body { color: red; }</style>
            </body>
        </html>
        """
        clean_html = HTMLSanitizer.sanitize_html(dirty_html)
        self.assertNotIn("<script>", clean_html)
        self.assertNotIn("<iframe>", clean_html)
        self.assertNotIn("<style>", clean_html)
        self.assertNotIn("onclick", clean_html)
        self.assertIn("<h1>Title</h1>", clean_html)
        self.assertIn("Safe content", clean_html)

    def test_clean_text_extraction(self):
        dirty_html = "<div><h1>Hello World</h1><script>ignore this</script>\u200B<p>Paragraph</p></div>"
        text = HTMLSanitizer.extract_clean_text(dirty_html)
        self.assertEqual(text, "Hello World Paragraph")

    def test_pii_redaction(self):
        text = "Pay with 4111-2222-3333-4444 or 1234 5678 9101 1121 safely."
        redacted = HTMLSanitizer.redact_pii(text)
        self.assertNotIn("4111-2222-3333-4444", redacted)
        self.assertNotIn("1234 5678 9101 1121", redacted)
        self.assertIn("[REDACTED_CREDIT_CARD]", redacted)

if __name__ == "__main__":
    unittest.main()
