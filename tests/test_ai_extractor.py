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

    @patch("src.extractor.ai_extractor.genai.Client")
    def test_schema_enforced_gemini_extraction(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"title": "Valid Book", "price": 24.99, "in_stock": true}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        extractor = AIExtractor(api_key="valid-gemini-key")
        result = extractor.extract("<html>Sample page content</html>", "Extract items", schema="product")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Valid Book")
        self.assertEqual(result[0]["price"], 24.99)
        self.assertTrue(result[0]["in_stock"])
        # Verify response_schema was configured
        call_kwargs = mock_client.models.generate_content.call_args[1]
        config = call_kwargs["config"]
        self.assertIsNotNone(config.response_schema)

    @patch("src.extractor.ai_extractor.genai.Client")
    def test_dynamic_string_schema_extraction(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"item_name": "Chair", "cost": 49.5}]'
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        extractor = AIExtractor(api_key="valid-gemini-key")
        result = extractor.extract(
            "<html>Sample</html>", 
            "Extract items", 
            schema="item_name:str,cost:float"
        )

        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["item_name"], "Chair")
        self.assertEqual(result[0]["cost"], 49.5)

if __name__ == "__main__":
    unittest.main()
