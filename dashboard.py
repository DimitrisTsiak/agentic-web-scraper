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
    page_title="Web Scraper Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean, formal, professional styling
st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .main-title {
        font-size: 2.0rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.25rem;
    }
    .main-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .status-active {
        color: #22c55e;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-inactive {
        color: #f59e0b;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("## Control Panel")
st.sidebar.markdown("---")

api_key = os.getenv("GEMINI_API_KEY", "")
if api_key and api_key != "your_gemini_api_key_here":
    st.sidebar.markdown('<span class="status-active">● Gemini API Configured</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="status-inactive">○ Gemini API Key Missing</span>', unsafe_allow_html=True)
    st.sidebar.caption("Set `GEMINI_API_KEY` in `.env` to enable LLM features.")

st.sidebar.markdown("---")
st.sidebar.subheader("Configuration")
ignore_robots = st.sidebar.checkbox("Bypass robots.txt", value=False, help="Allow fetching URLs restricted by robots.txt.")
timeout_sec = st.sidebar.slider("Timeout (seconds)", min_value=3, max_value=30, value=10)

# Header
st.markdown('<div class="main-title">Web Scraper Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Web content querying, structured data extraction, and multi-page crawling interface.</div>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_qa, tab_extract, tab_crawl = st.tabs([
    "Page Query",
    "Data Extraction",
    "Multi-Page Crawl"
])

# -----------------------------------------------------------------------------
# TAB 1: PAGE QUERY
# -----------------------------------------------------------------------------
with tab_qa:
    st.markdown("### Web Page Query")
    st.caption("Fetch a web page and query its content using natural language.")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_url = st.text_input("Target URL", value="https://books.toscrape.com/", placeholder="https://example.com")
    with col2:
        qa_model = st.selectbox("Model", options=["gemini-3.1-flash-lite"], index=0)

    user_question = st.text_area("Query", value="Are there any must-have computer science, python, or technical books available?", height=80)

    if st.button("Submit Query", type="primary", use_container_width=True):
        if not target_url.strip():
            st.error("Target URL is required.")
        elif not user_question.strip():
            st.error("Query prompt is required.")
        else:
            with st.spinner("Fetching target page..."):
                fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
                res = fetcher.fetch(target_url)

            if not res.success:
                st.error(f"Fetch failed: {res.error_message}")
            else:
                st.success(f"Page fetched (HTTP {res.status_code}, {res.elapsed_seconds:.2f}s)")
                
                with st.spinner("Processing query..."):
                    try:
                        qa_engine = AIQAEngine(model=qa_model)
                        qa_result = qa_engine.answer_question(res.clean_text, user_question)
                        
                        st.markdown("#### Response")
                        st.write(qa_result["answer"])
                        
                        with st.expander("Source Content Details"):
                            st.write(f"**Analyzed Length:** {qa_result['content_length']} characters")
                            st.write(f"**Model:** `{qa_result['model']}`")
                            st.text_area("Cleaned Page Text", value=res.clean_text[:3000] + ("..." if len(res.clean_text) > 3000 else ""), height=200, disabled=True)
                    except Exception as e:
                        st.error(f"Query processing error: {str(e)}")

# -----------------------------------------------------------------------------
# TAB 2: DATA EXTRACTION
# -----------------------------------------------------------------------------
with tab_extract:
    st.markdown("### Data Extraction")
    st.caption("Extract structured data records using natural language instructions or CSS rules.")

    extract_mode = st.radio("Extraction Method", options=["Natural Language Instruction", "CSS Selectors"], horizontal=True)
    extract_url = st.text_input("Target URL", value="https://books.toscrape.com/", key="ext_url")

    records = []
    if extract_mode == "Natural Language Instruction":
        col_p, col_s = st.columns([2, 1])
        with col_p:
            ai_prompt = st.text_area("Instruction", value="Extract all product titles and prices", height=70)
        with col_s:
            schema_choice = st.selectbox(
                "Schema Enforcement (Pydantic)", 
                options=["None (Free-form)", "Preset: Product", "Preset: Article", "Preset: Job Posting", "Custom Field Spec"],
                index=0
            )

        selected_schema = None
        if schema_choice == "Preset: Product":
            selected_schema = "product"
        elif schema_choice == "Preset: Article":
            selected_schema = "article"
        elif schema_choice == "Preset: Job Posting":
            selected_schema = "job"
        elif schema_choice == "Custom Field Spec":
            custom_spec = st.text_input("Field Specification", value="title:str,price:float,rating:float,in_stock:bool", help="Format: field:type,field2:type (e.g. title:str,price:float)")
            selected_schema = custom_spec.strip() if custom_spec.strip() else None

        if st.button("Run Extraction", type="primary", use_container_width=True):
            with st.spinner("Fetching and extracting data..."):
                fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
                res = fetcher.fetch(extract_url)
                if not res.success:
                    st.error(f"Fetch failed: {res.error_message}")
                else:
                    try:
                        extractor = AIExtractor()
                        data = extractor.extract(res.clean_text, ai_prompt, schema=selected_schema)
                        records = data if isinstance(data, list) else [data]
                        st.session_state["extracted_records"] = records
                    except Exception as e:
                        st.error(f"Extraction error: {str(e)}")

    else:  # CSS Selectors
        col_cont, col_fields = st.columns([1, 2])
        with col_cont:
            container_sel = st.text_input("Container Selector", value=".product_pod")
        with col_fields:
            fields_sel = st.text_input("Fields Mapping", value="title=h3 > a, price=.price_color, link=a::attr(href)")

        if st.button("Run Extraction", type="primary", use_container_width=True):
            with st.spinner("Fetching and extracting data..."):
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

    # Display Extracted Results
    extracted_data = st.session_state.get("extracted_records", [])
    if extracted_data:
        st.markdown(f"#### Results ({len(extracted_data)} items)")
        df = pd.DataFrame(extracted_data)
        st.dataframe(df, use_container_width=True)

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            json_str = json.dumps(extracted_data, indent=2, ensure_ascii=False)
            st.download_button("Export JSON", data=json_str, file_name="extracted_data.json", mime="application/json", use_container_width=True)
        with col_d2:
            csv_str = df.to_csv(index=False)
            st.download_button("Export CSV", data=csv_str, file_name="extracted_data.csv", mime="text/csv", use_container_width=True)
        with col_d3:
            md_str = DataExporter.to_markdown_table(extracted_data)
            st.download_button("Export Markdown", data=md_str, file_name="extracted_data.md", mime="text/markdown", use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: MULTI-PAGE CRAWLER
# -----------------------------------------------------------------------------
with tab_crawl:
    st.markdown("### Multi-Page Crawl")
    st.caption("Traverse paginated web pages sequentially and aggregate extracted datasets.")

    crawl_url = st.text_input("Starting URL", value="https://books.toscrape.com/", key="crawl_url")
    
    col_cp, col_cs = st.columns([2, 1])
    with col_cp:
        crawl_prompt = st.text_input("Extraction Instruction", value="Extract all product titles and prices", key="crawl_prompt")
    with col_cs:
        crawl_schema_choice = st.selectbox(
            "Schema Enforcement (Pydantic)", 
            options=["None (Free-form)", "Preset: Product", "Preset: Article", "Preset: Job Posting", "Custom Field Spec"],
            index=0,
            key="crawl_schema_choice"
        )

    crawl_schema = None
    if crawl_schema_choice == "Preset: Product":
        crawl_schema = "product"
    elif crawl_schema_choice == "Preset: Article":
        crawl_schema = "article"
    elif crawl_schema_choice == "Preset: Job Posting":
        crawl_schema = "job"
    elif crawl_schema_choice == "Custom Field Spec":
        crawl_spec = st.text_input("Field Specification", value="title:str,price:float,rating:float", key="crawl_spec")
        crawl_schema = crawl_spec.strip() if crawl_spec.strip() else None

    max_pages = st.slider("Maximum Pages", min_value=1, max_value=10, value=3)

    if st.button("Run Crawl", type="primary", use_container_width=True):
        fetcher = StaticFetcher(timeout=timeout_sec, ignore_robots=ignore_robots)
        crawler = MultiPageCrawler(fetcher=fetcher)
        
        progress_bar = st.progress(0)
        status_box = st.empty()
        status_box.info(f"Crawling starting from {crawl_url} (Limit: {max_pages} pages)...")

        try:
            records = crawler.crawl_and_extract(crawl_url, crawl_prompt, max_pages=max_pages, schema=crawl_schema)
            progress_bar.progress(100)
            status_box.success(f"Crawl finished. Extracted {len(records)} items across {max_pages} pages.")
            st.session_state["crawl_records"] = records
        except Exception as e:
            status_box.error(f"Crawl failed: {str(e)}")

    crawl_results = st.session_state.get("crawl_records", [])
    if crawl_results:
        st.markdown(f"#### Aggregated Results ({len(crawl_results)} items)")
        df_crawl = pd.DataFrame(crawl_results)
        st.dataframe(df_crawl, use_container_width=True)

        col_cd1, col_cd2 = st.columns(2)
        with col_cd1:
            json_crawl = json.dumps(crawl_results, indent=2, ensure_ascii=False)
            st.download_button("Export JSON", data=json_crawl, file_name="crawl_dataset.json", mime="application/json", use_container_width=True)
        with col_cd2:
            csv_crawl = df_crawl.to_csv(index=False)
            st.download_button("Export CSV", data=csv_crawl, file_name="crawl_dataset.csv", mime="text/csv", use_container_width=True)
