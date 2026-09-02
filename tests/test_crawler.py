import unittest
from unittest.mock import MagicMock
from src.crawler.crawler import MultiPageCrawler
from src.fetcher.models import FetchResult

class TestMultiPageCrawler(unittest.TestCase):
    def test_find_next_page_url_rel_next(self):
        crawler = MultiPageCrawler(fetcher=MagicMock(), ai_extractor=MagicMock())
        html = '<html><body><a rel="next" href="/page/2">Next Page</a></body></html>'
        next_url = crawler._find_next_page_url("https://example.com/page/1", html)
        self.assertEqual(next_url, "https://example.com/page/2")

    def test_find_next_page_url_text(self):
        crawler = MultiPageCrawler(fetcher=MagicMock(), ai_extractor=MagicMock())
        html = '<html><body><a href="?p=2">Next ></a></body></html>'
        next_url = crawler._find_next_page_url("https://example.com/items", html)
        self.assertEqual(next_url, "https://example.com/items?p=2")

    def test_crawl_and_extract_multi_page(self):
        mock_fetcher = MagicMock()
        mock_ai_extractor = MagicMock()

        # Page 1 fetch result
        res1 = FetchResult(
            url="https://example.com/page/1",
            status_code=200,
            success=True,
            raw_html='<html><body><h1>P1</h1><a rel="next" href="/page/2">Next</a></body></html>',
            clean_text="Page 1 Content"
        )
        # Page 2 fetch result
        res2 = FetchResult(
            url="https://example.com/page/2",
            status_code=200,
            success=True,
            raw_html='<html><body><h1>P2</h1></body></html>',
            clean_text="Page 2 Content"
        )

        mock_fetcher.fetch.side_effect = [res1, res2]
        mock_ai_extractor.extract.side_effect = [
            [{"title": "Item 1"}],
            [{"title": "Item 2"}]
        ]

        crawler = MultiPageCrawler(fetcher=mock_fetcher, ai_extractor=mock_ai_extractor)
        records = crawler.crawl_and_extract("https://example.com/page/1", "Extract titles", max_pages=3)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["title"], "Item 1")
        self.assertEqual(records[1]["title"], "Item 2")

    def test_crawl_and_extract_with_schema(self):
        mock_fetcher = MagicMock()
        mock_ai_extractor = MagicMock()

        res = FetchResult(
            url="https://example.com/page/1",
            status_code=200,
            success=True,
            raw_html='<html><body><h1>P1</h1></body></html>',
            clean_text="Page 1 Content"
        )
        mock_fetcher.fetch.return_value = res
        mock_ai_extractor.extract.return_value = [{"title": "Item 1", "price": 10.0}]

        crawler = MultiPageCrawler(fetcher=mock_fetcher, ai_extractor=mock_ai_extractor)
        records = crawler.crawl_and_extract(
            "https://example.com/page/1", 
            "Extract items", 
            max_pages=1, 
            schema="product"
        )

        self.assertEqual(len(records), 1)
        mock_ai_extractor.extract.assert_called_once_with(
            "Page 1 Content", "Extract items", schema="product", allow_file_lookup=False
        )

if __name__ == "__main__":
    unittest.main()
