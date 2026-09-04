import os
import uuid
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.fetcher.static_fetcher import StaticFetcher
from src.extractor.rule_extractor import RuleExtractor
from src.extractor.ai_extractor import AIExtractor
from src.agent.qa_engine import AIQAEngine
from src.crawler.crawler import MultiPageCrawler
from .schemas import (
    FetchRequest,
    FetchResponse,
    ExtractRequest,
    AIExtractRequest,
    QARequest,
    QAResponse,
    CrawlRequest,
    TaskStatusResponse,
)

app = FastAPI(
    title="Web Scraper Agent API",
    description="REST API for safe web scraping, AI natural language data extraction, grounded web Q&A, and multi-page crawling.",
    version="1.0.0",
)

# Configure CORS safely: allow local frontends by default or override via CORS_ORIGINS
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000")
if cors_origins_env.strip() == "*":
    allowed_origins = ["*"]
    allow_credentials = False
else:
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .storage import TaskStorage

# Persistent SQLite background task store
task_storage = TaskStorage()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Web Scraper Agent API",
        "version": "1.0.0",
        "endpoints": [
            "/api/fetch",
            "/api/extract",
            "/api/ai-extract",
            "/api/qa",
            "/api/crawl",
            "/api/tasks",
        ]
    }

@app.post("/api/fetch", response_model=FetchResponse)
def fetch_url(req: FetchRequest):
    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    res = fetcher.fetch(req.url)
    return FetchResponse(
        url=res.url,
        status_code=res.status_code,
        success=res.success,
        clean_text=res.clean_text,
        error_message=res.error_message,
        elapsed_seconds=res.elapsed_seconds,
    )

@app.post("/api/extract")
def extract_rules(req: ExtractRequest):
    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    res = fetcher.fetch(req.url)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error_message or "Fetch failed")

    records = RuleExtractor.extract_list(res.raw_html, req.container, req.fields, base_url=req.url)
    return {
        "url": req.url,
        "count": len(records),
        "records": records,
    }

from src.extractor.schemas import PRESET_SCHEMAS

def _resolve_request_schema(preset: Optional[str], fields: Optional[Dict[str, str]]) -> Optional[Any]:
    if preset:
        cleaned = preset.strip().lower()
        if cleaned not in PRESET_SCHEMAS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid schema_preset '{preset}'. Supported presets: {sorted(list(PRESET_SCHEMAS.keys()))}"
            )
        return cleaned
    if fields:
        return fields
    return None

@app.post("/api/ai-extract")
def extract_ai(req: AIExtractRequest):
    schema_arg = _resolve_request_schema(req.schema_preset, req.schema_fields)

    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    res = fetcher.fetch(req.url)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error_message or "Fetch failed")

    try:
        extractor = AIExtractor()
        data = extractor.extract(res.clean_text, req.prompt, schema=schema_arg, allow_file_lookup=False)
        records = data if isinstance(data, list) else [data]
        return {
            "url": req.url,
            "prompt": req.prompt,
            "count": len(records),
            "records": records,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qa", response_model=QAResponse)
def answer_web_qa(req: QARequest):
    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    res = fetcher.fetch(req.url)
    if not res.success:
        return QAResponse(
            url=req.url,
            question=req.question,
            answer="",
            success=False,
            error_message=res.error_message or "Failed to fetch webpage content."
        )

    try:
        qa_engine = AIQAEngine()
        result = qa_engine.answer_question(res.clean_text, req.question)
        return QAResponse(
            url=req.url,
            question=req.question,
            answer=result["answer"],
            success=True
        )
    except Exception as e:
        return QAResponse(
            url=req.url,
            question=req.question,
            answer="",
            success=False,
            error_message=str(e)
        )

def _run_crawl_task(task_id: str, req: CrawlRequest):
    task_storage.update_task_status(task_id, status="running")

    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    crawler = MultiPageCrawler(fetcher=fetcher)

    try:
        schema_arg = _resolve_request_schema(req.schema_preset, req.schema_fields)
        records = crawler.crawl_and_extract(
            req.url, req.prompt, max_pages=req.max_pages, schema=schema_arg, allow_file_lookup=False
        )
        task_storage.update_task_status(
            task_id, status="completed", records_count=len(records), records=records
        )
    except Exception as e:
        task_storage.update_task_status(task_id, status="failed", error_message=str(e))

@app.post("/api/crawl", response_model=TaskStatusResponse)
def start_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    # Validate schema upfront before creating background task
    _resolve_request_schema(req.schema_preset, req.schema_fields)

    task_id = str(uuid.uuid4())
    task_status = task_storage.create_task(task_id=task_id, url=req.url)

    background_tasks.add_task(_run_crawl_task, task_id, req)
    return task_status

@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    task = task_storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/tasks", response_model=List[TaskStatusResponse])
def list_tasks():
    return task_storage.list_tasks(limit=50, include_records=False)

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    deleted = task_storage.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "task_id": task_id}
