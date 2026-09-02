import uuid
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory background task registry
tasks_lock = threading.Lock()
tasks_db: Dict[str, TaskStatusResponse] = {}

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

    records = RuleExtractor.extract_list(res.raw_html, req.container, req.fields)
    return {
        "url": req.url,
        "count": len(records),
        "records": records,
    }

def _resolve_request_schema(preset: Optional[str], fields: Optional[Dict[str, str]]) -> Optional[Any]:
    if preset:
        return preset
    if fields:
        return fields
    return None

@app.post("/api/ai-extract")
def extract_ai(req: AIExtractRequest):
    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    res = fetcher.fetch(req.url)
    if not res.success:
        raise HTTPException(status_code=400, detail=res.error_message or "Fetch failed")

    try:
        extractor = AIExtractor()
        schema_arg = _resolve_request_schema(req.schema_preset, req.schema_fields)
        data = extractor.extract(res.clean_text, req.prompt, schema=schema_arg)
        records = data if isinstance(data, list) else [data]
        return {
            "url": req.url,
            "prompt": req.prompt,
            "count": len(records),
            "records": records,
        }
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
    with tasks_lock:
        tasks_db[task_id].status = "running"

    fetcher = StaticFetcher(ignore_robots=req.ignore_robots)
    crawler = MultiPageCrawler(fetcher=fetcher)

    try:
        schema_arg = _resolve_request_schema(req.schema_preset, req.schema_fields)
        records = crawler.crawl_and_extract(req.url, req.prompt, max_pages=req.max_pages, schema=schema_arg)
        with tasks_lock:
            tasks_db[task_id].status = "completed"
            tasks_db[task_id].records_count = len(records)
            tasks_db[task_id].records = records
    except Exception as e:
        with tasks_lock:
            tasks_db[task_id].status = "failed"
            tasks_db[task_id].error_message = str(e)

@app.post("/api/crawl", response_model=TaskStatusResponse)
def start_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task_status = TaskStatusResponse(
        task_id=task_id,
        status="pending",
        url=req.url,
        records_count=0,
        records=None,
        error_message=None,
    )
    with tasks_lock:
        tasks_db[task_id] = task_status

    background_tasks.add_task(_run_crawl_task, task_id, req)
    return task_status

@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    with tasks_lock:
        if task_id not in tasks_db:
            raise HTTPException(status_code=404, detail="Task not found")
        return tasks_db[task_id]

@app.get("/api/tasks", response_model=List[TaskStatusResponse])
def list_tasks():
    with tasks_lock:
        return list(tasks_db.values())
