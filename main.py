import argparse
import sys
import os
import subprocess
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
        description="Web Scraper Agent - CLI and Web Interface for web content fetching, data extraction, and querying."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command 1: fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a URL and return sanitized text content")
    fetch_parser.add_argument("--url", required=True, help="Target URL")
    fetch_parser.add_argument("--out", help="Output filepath (.txt or .html)")
    fetch_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions")

    # Command 2: extract
    extract_parser = subparsers.add_parser("extract", help="Extract structured records using CSS selectors")
    extract_parser.add_argument("--url", required=True, help="Target URL")
    extract_parser.add_argument("--container", required=True, help="CSS selector for repeated container item (e.g. '.product-card')")
    extract_parser.add_argument("--fields", required=True, help="Field mapping (e.g. 'title=.name,price=.price,link=a::attr(href)')")
    extract_parser.add_argument("--out", required=True, help="Output filepath (.json, .csv, or .md)")
    extract_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions")

    # Command 3: ai-extract
    ai_parser = subparsers.add_parser("ai-extract", help="Extract structured data using natural language instructions")
    ai_parser.add_argument("--url", required=True, help="Target URL")
    ai_parser.add_argument("--prompt", required=True, help="Extraction instruction prompt")
    ai_parser.add_argument("--out", required=True, help="Output filepath (.json, .csv, or .md)")
    ai_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions")

    # Command 4: qa
    qa_parser = subparsers.add_parser("qa", help="Query web page content using natural language")
    qa_parser.add_argument("--url", required=True, help="Target URL")
    qa_parser.add_argument("--question", required=True, help="Query string")
    qa_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions")

    # Command 5: crawl
    crawl_parser = subparsers.add_parser("crawl", help="Crawl paginated web pages and extract aggregated data")
    crawl_parser.add_argument("--url", required=True, help="Starting URL")
    crawl_parser.add_argument("--prompt", required=True, help="Extraction instruction prompt")
    crawl_parser.add_argument("--max-pages", type=int, default=3, help="Maximum pages to crawl (default: 3)")
    crawl_parser.add_argument("--out", required=True, help="Output filepath (.json, .csv, or .md)")
    crawl_parser.add_argument("--ignore-robots", action="store_true", help="Bypass robots.txt restrictions")


    # Command 6: server (launches FastAPI REST server)
    server_parser = subparsers.add_parser("server", help="Launch FastAPI REST API server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    server_parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")

    # Command 7: dashboard (launches Streamlit Web Dashboard)
    dash_parser = subparsers.add_parser("dashboard", help="Launch Streamlit Web Dashboard UI")
    dash_parser.add_argument("--port", type=int, default=8501, help="Port number (default: 8501)")

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

    elif args.command == "qa":
        from src.agent.qa_engine import AIQAEngine

        print(f"[AGENT] Safely fetching URL: {args.url}")
        result = fetcher.fetch(args.url)

        if not result.success:
            print(f"[ERROR] {result.error_message}")
            sys.exit(1)

        print(f"[AGENT] Asking AI Q&A Engine: '{args.question}'...")
        try:
            qa_engine = AIQAEngine()
            qa_res = qa_engine.answer_question(result.clean_text, args.question)
            print("\n" + "="*50)
            print(f"QUESTION: {args.question}")
            print("="*50)
            print(qa_res["answer"])
            print("="*50 + "\n")
        except Exception as e:
            print(f"[ERROR] {str(e)}")
            sys.exit(1)

    elif args.command == "crawl":
        from src.crawler.crawler import MultiPageCrawler

        print(f"[AGENT] Starting multi-page crawl starting at: {args.url} (max_pages={args.max_pages})")
        crawler = MultiPageCrawler(fetcher=fetcher)

        records = crawler.crawl_and_extract(args.url, args.prompt, max_pages=args.max_pages)
        print(f"[AGENT] Crawl complete. Extracted a total of {len(records)} record(s) across pages.")

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

    elif args.command == "server":
        import uvicorn
        print(f"[AGENT] Starting FastAPI REST API server at http://{args.host}:{args.port}")
        uvicorn.run("src.api.app:app", host=args.host, port=args.port, reload=False)

    elif args.command == "dashboard":
        print(f"[AGENT] Launching Streamlit Web Dashboard on port {args.port}...")
        cmd = [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--server.port", str(args.port)]
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
