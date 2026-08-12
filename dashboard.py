import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.fetcher.static_fetcher import StaticFetcher
from src.extractor.rule_extractor import RuleExtractor
from src.extractor.ai_extractor import AIExtractor
from src.extractor.exporter import DataExporter
from src.agent.qa_engine import AIQAEngine
from src.crawler.crawler import MultiPageCrawler

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Web Scraper Agent Dashboard",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    /* Dark / Sleek Theme Overrides */
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #9CA3AF;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #1F2937;
        border-radius: 10px;
        padding: 1.25rem;
        border: 1px solid #374151;
        margin-bottom: 1rem;
    }
    .badge-success {
        background-color: #065F46;
        color: #34D399;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-warning {
        background-color: #78350F;
        color: #FBBF24;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/isometric-line/96/spider.png", width=64)
st.sidebar.markdown("## 🕷️ Web Scraper Agent")
st.sidebar.markdown("---")

api_key = os.getenv("GEMINI_API_KEY", "")
if api_key and api_key != "your_gemini_api_key_here":
    st.sidebar.markdown('<span class="badge-success">✓ Gemini API Connected</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="badge-warning">⚠️ Gemini API Key Missing</span>', unsafe_allow_html=True)
    st.sidebar.caption("Please configure `GEMINI_API_KEY` in `.env` to enable AI Q&A and AI Extraction.")

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Safety Settings")
ignore_robots = st.sidebar.checkbox("Ignore robots.txt", value=False, help="Bypass robots.txt restrictions (use responsibly).")
timeout_sec = st.sidebar.slider("Request Timeout (s)", min_value=3, max_value=30, value=10)

st.sidebar.markdown("---")
st.sidebar.caption("Built with FastAPI, Streamlit, and Google Gemini.")

# Header
st.markdown('<div class="main-header">Web Scraper Agent Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Safe, polite web content fetching, natural language Q&A, AI data extraction, and multi-page crawling</div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_qa, tab_extract, tab_crawl = st.tabs([
    "💬 Web Q&A Assistant",
    "🔍 Scrape & Extract Data",
    "🕷️ Multi-Page Crawler"
])

# -----------------------------------------------------------------------------
# TAB 1: WEB Q&A ASSISTANT
# -----------------------------------------------------------------------------
with tab_qa:
    st.markdown("### 💬 Ask Questions Grounded in Web Content")
    st.markdown("Provide any website URL and ask questions directly. The LLM parses the fetched web page and provides grounded answers.")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_url = st.text_input("Target Website URL", value="https://books.toscrape.com/", placeholder="https://example.com")
    with col2:
        qa_model = st.selectbox("AI Model", options=["gemini-3.1-flash-lite"], index=0)

    user_question = st.text_area("Your Question", value="Are there any must-have computer science, python, or technical books available?", height=80)

    if st.button("🔍 Fetch & Ask LLM", type="primary", use_container_width=True):
        if not target_url.strip():
            st.error("Please enter a valid target URL.")
        elif not user_question.strip():
            st.error("Please enter a question to ask.")
        else:
            with st.spinner("Safely fetching target page content..."):
                fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
                res = fetcher.fetch(target_url)

            if not res.success:
                st.error(f"Failed to fetch webpage: {res.error_message}")
            else:
                st.success(f"Fetched page successfully! Status: {res.status_code} ({res.elapsed_seconds:.2f}s)")
                
                with st.spinner("Analyzing content with Gemini AI Q&A Engine..."):
                    try:
                        qa_engine = AIQAEngine(model=qa_model)
                        qa_result = qa_engine.answer_question(res.clean_text, user_question)
                        
                        st.markdown("#### 🤖 LLM Answer")
                        st.info(qa_result["answer"])
                        
                        with st.expander("📄 View Source Page Preview & Metadata"):
                            st.write(f"**Analyzed Text Length:** {qa_result['content_length']} characters")
                            st.write(f"**Model Used:** `{qa_result['model']}`")
                            st.text_area("Extracted Webpage Text", value=res.clean_text[:3000] + ("..." if len(res.clean_text) > 3000 else ""), height=200, disabled=True)
                    except Exception as e:
                        st.error(f"AI Q&A failed: {str(e)}")

# -----------------------------------------------------------------------------
# TAB 2: SCRAPE & EXTRACT DATA
# -----------------------------------------------------------------------------
with tab_extract:
    st.markdown("### 🔍 Extract Structured Data")
    st.markdown("Scrape tabular records using AI Natural Language Prompts or CSS Selectors.")

    extract_mode = st.radio("Extraction Method", options=["AI Natural Language Prompt", "CSS Selectors"], horizontal=True)
    extract_url = st.text_input("Target URL to Extract", value="https://books.toscrape.com/", key="ext_url")

    records = []
    if extract_mode == "AI Natural Language Prompt":
        ai_prompt = st.text_area("Natural Language Extraction Goal", value="Extract all product titles and prices", height=70)
        if st.button("🚀 Run AI Extraction", type="primary", use_container_width=True):
            with st.spinner("Fetching and extracting using Gemini AI..."):
                fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
                res = fetcher.fetch(extract_url)
                if not res.success:
                    st.error(f"Fetch failed: {res.error_message}")
                else:
                    try:
                        extractor = AIExtractor()
                        data = extractor.extract(res.clean_text, ai_prompt)
                        records = data if isinstance(data, list) else [data]
                        st.session_state["extracted_records"] = records
                    except Exception as e:
                        st.error(f"Extraction error: {str(e)}")

    else:  # CSS Selectors
        col_cont, col_fields = st.columns([1, 2])
        with col_cont:
            container_sel = st.text_input("Item Container Selector", value=".product_pod")
        with col_fields:
            fields_sel = st.text_input("Fields Mapping (name=selector)", value="title=h3 > a, price=.price_color, link=a::attr(href)")

        if st.button("⚡ Run Rule Extraction", type="primary", use_container_width=True):
            with st.spinner("Fetching and applying CSS selectors..."):
                fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
                res = fetcher.fetch(extract_url)
                if not res.success:
                    st.error(f"Fetch failed: {res.error_message}")
                else:
                    fields_dict = {}
                    for pair in fields_sel.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            fields_dict[k.strip()] = v.strip()
                    
                    records = RuleExtractor.extract_list(res.raw_html, container_sel, fields_dict)
                    st.session_state["extracted_records"] = records

    # Display Extracted Results if present
    extracted_data = st.session_state.get("extracted_records", [])
    if extracted_data:
        st.markdown(f"#### 📊 Extracted Results ({len(extracted_data)} items)")
        df = pd.DataFrame(extracted_data)
        st.dataframe(df, use_container_width=True)

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            json_str = json.dumps(extracted_data, indent=2, ensure_ascii=False)
            st.download_button("📥 Download JSON", data=json_str, file_name="extracted_data.json", mime="application/json", use_container_width=True)
        with col_d2:
            csv_str = df.to_csv(index=False)
            st.download_button("📥 Download CSV", data=csv_str, file_name="extracted_data.csv", mime="text/csv", use_container_width=True)
        with col_d3:
            md_str = DataExporter.to_markdown_table(extracted_data)
            st.download_button("📥 Download Markdown", data=md_str, file_name="extracted_data.md", mime="text/markdown", use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: MULTI-PAGE CRAWLER
# -----------------------------------------------------------------------------
with tab_crawl:
    st.markdown("### 🕷️ Multi-Page Pagination Crawler")
    st.markdown("Crawl across paginated websites automatically and combine extracted dataset using AI.")

    crawl_url = st.text_input("Starting URL", value="https://books.toscrape.com/", key="crawl_url")
    crawl_prompt = st.text_input("Extraction Goal Prompt", value="Extract all product titles and prices", key="crawl_prompt")
    max_pages = st.slider("Max Pages to Crawl", min_value=1, max_value=10, value=3)

    if st.button("🕷️ Start Multi-Page Crawl", type="primary", use_container_width=True):
        fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
        crawler = MultiPageCrawler(fetcher=fetcher)
        
        progress_bar = st.progress(0)
        status_box = st.empty()
        status_box.info(f"Starting crawl at {crawl_url} (Max pages: {max_pages})...")

        try:
            records = crawler.crawl_and_extract(crawl_url, crawl_prompt, max_pages=max_pages)
            progress_bar.progress(100)
            status_box.success(f"Crawl completed! Extracted {len(records)} records across pages.")
            st.session_state["crawl_records"] = records
        except Exception as e:
            status_box.error(f"Crawl error: {str(e)}")

    crawl_results = st.session_state.get("crawl_records", [])
    if crawl_results:
        st.markdown(f"#### 📊 Aggregated Dataset ({len(crawl_results)} items)")
        df_crawl = pd.DataFrame(crawl_results)
        st.dataframe(df_crawl, use_container_width=True)

        col_cd1, col_cd2 = st.columns(2)
        with col_cd1:
            json_crawl = json.dumps(crawl_results, indent=2, ensure_ascii=False)
            st.download_button("📥 Download Crawl JSON", data=json_crawl, file_name="crawl_dataset.json", mime="application/json", use_container_width=True)
        with col_cd2:
            csv_crawl = df_crawl.to_csv(index=False)
            st.download_button("📥 Download Crawl CSV", data=csv_crawl, file_name="crawl_dataset.csv", mime="text/csv", use_container_width=True)
