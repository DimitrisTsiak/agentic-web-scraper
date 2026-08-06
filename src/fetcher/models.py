from pydantic import BaseModel, Field
from typing import Dict, Optional

class FetchResult(BaseModel):
    """Encapsulates the response data of a web fetch operation."""
    url: str
    status_code: int
    success: bool
    raw_html: str = ""
    clean_text: str = ""
    error_message: Optional[str] = None
    elapsed_seconds: float = 0.0
    headers: Dict[str, str] = Field(default_factory=dict)
