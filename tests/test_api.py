import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Web Scraper Agent API" in data["service"]

def test_cors_allowed_and_blocked_origins():
    res_allowed = client.options(
        "/",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:8501"

    res_blocked = client.options(
        "/",
        headers={
            "Origin": "http://malicious-site.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert res_blocked.headers.get("access-control-allow-origin") is None

@patch("src.api.app.StaticFetcher")
def test_fetch_endpoint(mock_fetcher_cls):
    mock_instance = MagicMock()
    mock_fetch_result = MagicMock()
    mock_fetch_result.url = "https://example.com"
    mock_fetch_result.status_code = 200
    mock_fetch_result.success = True
    mock_fetch_result.clean_text = "Hello Example Domain"
    mock_fetch_result.error_message = None
    mock_fetch_result.elapsed_seconds = 0.12
    mock_instance.fetch.return_value = mock_fetch_result
    mock_fetcher_cls.return_value = mock_instance

    response = client.post("/api/fetch", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["clean_text"] == "Hello Example Domain"

@patch("src.api.app.AIQAEngine")
@patch("src.api.app.StaticFetcher")
def test_qa_endpoint(mock_fetcher_cls, mock_qa_cls):
    mock_fetcher = MagicMock()
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.clean_text = "Python Programming Book for $30"
    mock_fetcher.fetch.return_value = mock_res
    mock_fetcher_cls.return_value = mock_fetcher

    mock_qa = MagicMock()
    mock_qa.answer_question.return_value = {
        "answer": "Yes, Python Programming Book is available for $30.",
        "model": "gemini-3.1-flash-lite",
        "content_length": 30
    }
    mock_qa_cls.return_value = mock_qa

    response = client.post("/api/qa", json={"url": "https://example.com", "question": "Are there CS books?"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Python Programming Book" in data["answer"]

def test_crawl_task_creation_and_status():
    with patch("src.api.app.MultiPageCrawler") as mock_crawler_cls, \
         patch("src.api.app.StaticFetcher"):
        mock_crawler = MagicMock()
        mock_crawler.crawl_and_extract.return_value = [{"title": "Book 1", "price": "$10"}]
        mock_crawler_cls.return_value = mock_crawler

        response = client.post("/api/crawl", json={"url": "https://example.com", "prompt": "Extract books", "max_pages": 1})
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        task_id = data["task_id"]

        # Fetch status
        status_res = client.get(f"/api/tasks/{task_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["task_id"] == task_id

@patch("src.api.app.AIExtractor")
@patch("src.api.app.StaticFetcher")
def test_ai_extract_endpoint_with_schema(mock_fetcher_cls, mock_extractor_cls):
    mock_fetcher = MagicMock()
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.clean_text = "Page with books"
    mock_fetcher.fetch.return_value = mock_res
    mock_fetcher_cls.return_value = mock_fetcher

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = [{"title": "Python Book", "price": 29.99}]
    mock_extractor_cls.return_value = mock_extractor

    response = client.post(
        "/api/ai-extract",
        json={
            "url": "https://example.com",
            "prompt": "Extract products",
            "schema_preset": "product"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["records"][0]["title"] == "Python Book"
    mock_extractor.extract.assert_called_once_with(
        "Page with books", "Extract products", schema="product", allow_file_lookup=False
    )

def test_ai_extract_rejects_arbitrary_file_preset():
    response = client.post(
        "/api/ai-extract",
        json={
            "url": "https://example.com",
            "prompt": "Extract products",
            "schema_preset": "../../sensitive_config.json"
        }
    )
    assert response.status_code == 400
    assert "Invalid schema_preset" in response.json()["detail"]

def test_delete_task_endpoint():
    with patch("src.api.app.MultiPageCrawler"), patch("src.api.app.StaticFetcher"):
        res = client.post("/api/crawl", json={"url": "https://example.com/crawl", "prompt": "items", "max_pages": 1})
        assert res.status_code == 200
        task_id = res.json()["task_id"]

        del_res = client.delete(f"/api/tasks/{task_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        get_res = client.get(f"/api/tasks/{task_id}")
        assert get_res.status_code == 404



