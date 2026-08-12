# Web Scraper Agent

A web scraping application supporting Google Gemini AI querying, structured data extraction, multi-page crawling, and a Streamlit Web Dashboard.

## Features

- **Security and Compliance**: Protocol validation (HTTP/HTTPS only), robots.txt parsing, domain rate limiting, and HTML script/payload sanitization.
- **Web Dashboard**: Streamlit GUI for web content querying, data extraction, and crawl monitoring.
- **AI-Powered Q&A**: Natural language web page querying powered by Google Gemini (`gemini-3.1-flash-lite`) via the official Google Gen AI SDK.
- **AI & Rule-Based Extraction**: Natural language data extraction or CSS selector rule parsing.
- **Multi-Page Crawler**: Automated pagination link detection and multi-page dataset aggregation.
- **Data Exporting**: Export extracted records into JSON, CSV, or Markdown table formats.

## Installation

1. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Copy `.env.example` to `.env` and set your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.1-flash-lite
   ```

## Usage

### Web Application

Launch the Web Dashboard interface for web page querying, structured data extraction, and multi-page crawl tracking:
```bash
python main.py dashboard
```
*Access the Web Dashboard in your browser at `http://localhost:8501`.*

---

### CLI Usage

#### 1. Fetch Web Page Content
Fetch a URL, sanitize HTML, and print or save clean text:
```bash
python main.py fetch --url "https://example.com" --out "output/clean_text.txt"
```

#### 2. Web Page Q&A (Google Gemini)
Query webpage content using natural language:
```bash
python main.py qa --url "https://books.toscrape.com/" --question "Are there any must-have computer science books available?"
```

#### 3. AI-Powered Extraction (Google Gemini)
Extract structured data from any single web page using a natural language prompt:
```bash
python main.py ai-extract --url "https://books.toscrape.com/" --prompt "Extract all book titles and prices" --out "output/books.json"
```

#### 4. Multi-Page Crawler
Crawl across multiple paginated pages and combine extracted datasets:
```bash
python main.py crawl --url "https://books.toscrape.com/" --prompt "Extract all book titles and prices" --max-pages 5 --out "output/all_books.csv"
```

## Project Structure

```
web-scrapper-agent/
├── main.py                   # CLI & app server entrypoint
├── dashboard.py              # Streamlit Web Dashboard application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── src/
│   ├── agent/                # AI Q&A Engine (Google Gen AI SDK)
│   ├── api/                  # FastAPI service app & Pydantic schemas
│   ├── safety/               # SSRF, robots.txt, rate limiter, and sanitizer
│   ├── fetcher/              # HTTP fetcher engine and models
│   ├── extractor/            # AI (Gemini) extractor, rule extractor, and exporter
│   └── crawler/              # Multi-page pagination crawler module
└── output/                   # Generated output files
```
