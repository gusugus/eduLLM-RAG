# core/models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    text: str
    n_results: int = 5

class ResultItem(BaseModel):
    id: str
    document: str
    metadata: Dict[str, Any]
    score: float