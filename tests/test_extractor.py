import unittest
import os
import json
import csv
import tempfile
from src.extractor.rule_extractor import RuleExtractor
from src.extractor.exporter import DataExporter

class TestExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_html = """
        <div class="product-list">
            <div class="product-card">
                <h2 class="title">Product A</h2>
                <span class="price">$10.00</span>
                <a class="link" href="/item/a">View</a>
            </div>
            <div class="product-card">
                <h2 class="title">Product B</h2>
                <span class="price">$20.00</span>
                <a class="link" href="/item/b">View</a>
            </div>
        </div>
        """

    def test_extract_list(self):
        results = RuleExtractor.extract_list(
            self.sample_html,
            item_selector=".product-card",
            fields={
                "name": ".title",
                "price": ".price",
                "link": "a::attr(href)"
            }
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Product A")
        self.assertEqual(results[0]["price"], "$10.00")
        self.assertEqual(results[0]["link"], "/item/a")
        self.assertEqual(results[1]["name"], "Product B")

    def test_exporter(self):
        records = [
            {"name": "Item 1", "price": "$10"},
            {"name": "Item 2", "price": "$20"}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "out.json")
            csv_path = os.path.join(tmpdir, "out.csv")

            DataExporter.to_json(records, json_path)
            self.assertTrue(os.path.exists(json_path))
            with open(json_path, "r") as f:
                loaded = json.load(f)
                self.assertEqual(len(loaded), 2)

            DataExporter.to_csv(records, csv_path)
            self.assertTrue(os.path.exists(csv_path))

            md_table = DataExporter.to_markdown_table(records)
            self.assertIn("| Item 1 | $10 |", md_table)

    def test_extract_list_resolves_relative_urls(self):
        results = RuleExtractor.extract_list(
            self.sample_html,
            item_selector=".product-card",
            fields={
                "name": ".title",
                "link": "a::attr(href)"
            },
            base_url="https://example.com/store/catalog/page.html"
        )
        self.assertEqual(len(results), 2)
        # Root-relative link '/item/a' resolved against base_url
        self.assertEqual(results[0]["link"], "https://example.com/item/a")
        self.assertEqual(results[1]["link"], "https://example.com/item/b")

    def test_extract_single_resolves_relative_urls(self):
        html = '<div class="product"><a href="../details.html">Details</a><img src="../../img.png"></div>'
        result = RuleExtractor.extract_single(
            html,
            fields={
                "link": "a::attr(href)",
                "image": "img::attr(src)"
            },
            base_url="https://example.com/a/b/index.html"
        )
        self.assertEqual(result["link"], "https://example.com/a/details.html")
        self.assertEqual(result["image"], "https://example.com/img.png")

if __name__ == "__main__":
    unittest.main()
