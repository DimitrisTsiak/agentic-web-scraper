import unittest
from unittest.mock import patch, MagicMock
from src.extractor.ai_extractor import AIExtractor

class TestAIExtractor(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        extractor = AIExtractor(api_key="your_gemini_api_key_here")
        with self.assertRaises(ValueError) as ctx:
            extractor.extract("Sample text", "Extract title")
        self.assertIn("GEMINI_API_KEY is not configured", str(ctx.exception))

    @patch("src.extractor.ai_extractor.genai.Client")
    def test_successful_gemini_ai_extraction(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Gemini Item", "price": "$15"}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        extractor = AIExtractor(api_key="valid-gemini-key")
        result = extractor.extract("<html>Sample page content</html>", "Extract items")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Gemini Item")
        self.assertEqual(result[0]["price"], "$15")

if __name__ == "__main__":
    unittest.main()
