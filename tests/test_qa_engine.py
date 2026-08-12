import pytest
from unittest.mock import patch, MagicMock
from src.agent.qa_engine import AIQAEngine

def test_qa_engine_missing_api_key():
    engine = AIQAEngine(api_key="your_gemini_api_key_here")
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        engine.answer_question("Some webpage text", "Are there CS books?")

def test_qa_engine_empty_text():
    engine = AIQAEngine(api_key="fake_key")
    result = engine.answer_question("", "Are there CS books?")
    assert "No content was extracted" in result["answer"]
    assert result["content_length"] == 0

@patch("src.agent.qa_engine.requests.post")
def test_qa_engine_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Yes, 'Designing Data-Intensive Applications' is available for $45.00."}]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    engine = AIQAEngine(api_key="test_api_key")
    result = engine.answer_question("Book: Designing Data-Intensive Applications, Price: $45.00", "What CS books are available?")

    assert "Designing Data-Intensive Applications" in result["answer"]
    assert result["model"] == "gemini-3.1-flash-lite"
    assert result["content_length"] > 0
