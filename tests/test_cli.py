import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json
from main import parse_fields_arg, build_cli

class TestCLIWorkflow(unittest.TestCase):
    def test_parse_fields_arg(self):
        arg = "title=.titleline > a, link=a::attr(href), score=.score"
        parsed = parse_fields_arg(arg)
        self.assertEqual(parsed["title"], ".titleline > a")
        self.assertEqual(parsed["link"], "a::attr(href)")
        self.assertEqual(parsed["score"], ".score")

    def test_cli_argument_parsing(self):
        parser = build_cli()
        args = parser.parse_args(["extract", "--url", "https://example.com", "--container", ".item", "--fields", "name=.title", "--out", "test.json"])
        self.assertEqual(args.command, "extract")
        self.assertEqual(args.url, "https://example.com")
        self.assertEqual(args.container, ".item")

    def test_cli_ai_extract_with_schema(self):
        parser = build_cli()
        args = parser.parse_args([
            "ai-extract", 
            "--url", "https://example.com", 
            "--prompt", "Extract products", 
            "--schema", "product", 
            "--out", "out.json"
        ])
        self.assertEqual(args.command, "ai-extract")
        self.assertEqual(args.schema, "product")

    def test_cli_crawl_with_schema(self):
        parser = build_cli()
        args = parser.parse_args([
            "crawl", 
            "--url", "https://example.com", 
            "--prompt", "Extract jobs", 
            "--schema", "title:str,salary:float", 
            "--out", "out.csv"
        ])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.schema, "title:str,salary:float")

if __name__ == "__main__":
    unittest.main()
