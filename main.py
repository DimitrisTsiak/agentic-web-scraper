import argparse
import sys
import os
from typing import Dict

# Fix Windows console encoding issues if needed
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.safety.url_validator import validate_url
from src.fetcher.static_fetcher import StaticFetcher
from src.extractor.rule_extractor import RuleExtractor
from src.extractor.exporter import DataExporter

def parse_fields_arg(fields_str: str) -> Dict[str, str]:
    """
    Parses field mapping string format: 'title=.titleline > a,link=a::attr(href)'
    """
    fields = {}
    if not fields_str:
        return fields

    pairs = fields_str.split(",")
    for pair in pairs:
        if "=" in pair:
            key, val = pair.split("=", 1)
            fields[key.strip()] = val.strip()
    return fields

def build_cli():
    parser = argparse.ArgumentParser(
        description="[Web Scraper Agent] Safe, polite, and structured web scraping CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command 1: fetch (fetches HTML/text with safety checks)
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a URL safely and display or save clean text")
    fetch_parser.add_argument("--url", required=True, help="Target website URL")
    fetch_parser.add_argument("--out", help="Optional output filepath (.txt or .html)")
    fetch_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions (use responsibly)")

    # Command 2: extract (scrapes structured items using CSS rules)
    extract_parser = subparsers.add_parser("extract", help="Extract structured records using CSS rules")
    extract_parser.add_argument("--url", required=True, help="Target website URL")
    extract_parser.add_argument("--container", required=True, help="CSS selector for repeated container item (e.g. '.product-card')")
    extract_parser.add_argument("--fields", required=True, help="Field mapping e.g. 'title=.name,price=.price,link=a::attr(href)'")
    extract_parser.add_argument("--out", required=True, help="Output filepath (.json, .csv, or .md)")
    extract_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions (use responsibly)")

    # Command 3: ai-extract (scrapes structured items using AI natural language prompt)
    ai_parser = subparsers.add_parser("ai-extract", help="Extract structured data using AI natural language prompt")
    ai_parser.add_argument("--url", required=True, help="Target website URL")
    ai_parser.add_argument("--prompt", required=True, help="Natural language extraction goal e.g. 'Extract all product names, prices, and ratings'")
    ai_parser.add_argument("--out", required=True, help="Output filepath (.json, .csv, or .md)")
    ai_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions (use responsibly)")

    return parser



def main():
    parser = build_cli()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    ignore_robots = getattr(args, "ignore_robots", False)
    fetcher = StaticFetcher(ignore_robots=ignore_robots)


    if args.command == "fetch":
        print(f"[AGENT] Safely fetching URL: {args.url}")
        result = fetcher.fetch(args.url)

        if not result.success:
            print(f"[ERROR] {result.error_message}")
            sys.exit(1)

        print(f"[SUCCESS] Status {result.status_code} ({result.elapsed_seconds:.2f}s)")
        print("-" * 50)
        preview = result.clean_text[:500] + ("..." if len(result.clean_text) > 500 else "")
        print(preview)
        print("-" * 50)

        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(result.clean_text)
            print(f"[SAVED] Cleaned text saved to: {args.out}")

    elif args.command == "extract":
        print(f"[AGENT] Safely fetching & parsing URL: {args.url}")
        result = fetcher.fetch(args.url)

        if not result.success:
            print(f"[ERROR] {result.error_message}")
            sys.exit(1)

        fields_map = parse_fields_arg(args.fields)
        if not fields_map:
            print("[ERROR] Invalid --fields argument format. Expected 'field1=selector1,field2=selector2'")
            sys.exit(1)

        records = RuleExtractor.extract_list(result.raw_html, args.container, fields_map)
        print(f"[AGENT] Extracted {len(records)} record(s).")

        out_path = args.out
        if out_path.endswith(".json"):
            DataExporter.to_json(records, out_path)
        elif out_path.endswith(".csv"):
            DataExporter.to_csv(records, out_path)
        elif out_path.endswith(".md"):
            md_content = DataExporter.to_markdown_table(records)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md_content)
        else:
            DataExporter.to_json(records, out_path)

        print(f"[SAVED] Results exported to: {out_path}")
        print("\nPreview:")
        print(DataExporter.to_markdown_table(records[:5]))

    elif args.command == "ai-extract":
        from src.extractor.ai_extractor import AIExtractor

        print(f"[AGENT] Safely fetching URL: {args.url}")
        result = fetcher.fetch(args.url)

        if not result.success:
            print(f"[ERROR] {result.error_message}")
            sys.exit(1)

        print(f"[AGENT] Running AI extraction with prompt: '{args.prompt}'...")
        try:
            ai_extractor = AIExtractor()
            extracted_data = ai_extractor.extract(result.clean_text, args.prompt)
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            sys.exit(1)

        records = extracted_data if isinstance(extracted_data, list) else [extracted_data]
        print(f"[AGENT] Extracted {len(records)} record(s).")

        out_path = args.out
        if out_path.endswith(".json"):
            DataExporter.to_json(records, out_path)
        elif out_path.endswith(".csv"):
            DataExporter.to_csv(records, out_path)
        elif out_path.endswith(".md"):
            md_content = DataExporter.to_markdown_table(records)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md_content)
        else:
            DataExporter.to_json(records, out_path)

        print(f"[SAVED] Results exported to: {out_path}")
        if records:
            print("\nPreview:")
            print(DataExporter.to_markdown_table(records[:5]))


if __name__ == "__main__":
    main()
