# Web Scraper Agent

A safe, polite, and modular web scraping CLI agent with support for Google Gemini AI natural language parsing and structured data exporting.

## Features

- Safety and Compliance: SSRF protection, protocol whitelisting (HTTP/HTTPS only), robots.txt parsing, domain rate limiting, and HTML script/payload sanitization.
- Static Fetching Engine: Fast HTTP page fetching with automatic content cleanup and error handling.
- AI-Powered Extraction: Natural language data parsing using Google Gemini 3.1 Flash-Lite (`gemini-3.1-flash-lite`).
- Data Exporting: Export extracted records into JSON, CSV, or Markdown table formats.

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

### 1. Fetch Web Page Content
Safely fetch a URL, sanitize HTML, and print or save clean text:
```bash
python main.py fetch --url "https://example.com" --out "output/clean_text.txt"
```

### 2. AI-Powered Extraction (Google Gemini)
Extract structured data from any web page using a natural language prompt:
```bash
python main.py ai-extract --url "https://books.toscrape.com/" --prompt "Extract all book titles and prices" --out "output/books.json"
```

## Project Structure

```
web-scrapper-agent/
├── main.py                   # CLI entrypoint
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── src/
│   ├── safety/               # SSRF, robots.txt, rate limiter, and sanitizer
│   ├── fetcher/              # HTTP fetcher engine and models
│   └── extractor/            # AI (Gemini) extractor and exporter modules
└── output/                   # Generated output files
```
