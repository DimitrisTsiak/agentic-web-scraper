from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class FetchRequest(BaseModel):
    url: str
    ignore_robots: bool = False

class FetchResponse(BaseModel):
    url: str
    status_code: int
    success: bool
    clean_text: str = ""
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0

class ExtractRequest(BaseModel):
    url: str
    container: str
    fields: Dict[str, str]
    ignore_robots: bool = False

class AIExtractRequest(BaseModel):
    url: str
    prompt: str
    ignore_robots: bool = False

class QARequest(BaseModel):
    url: str
    question: str
    ignore_robots: bool = False

class QAResponse(BaseModel):
    url: str
    question: str
    answer: str
    success: bool
    error_message: Optional[str] = None

class CrawlRequest(BaseModel):
    url: str
    prompt: str
    max_pages: int = Field(default=3, ge=1, le=20)
    ignore_robots: bool = False

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    url: str
    records_count: int = 0
    records: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
