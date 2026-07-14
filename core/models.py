# core/models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    text: str
    n_results: int = 5
    min_score: float = 0.7

class ResultItem(BaseModel):
    id: str
    document: str
    metadata: Dict[str, Any]
    score: float

class TemaSubtemas(BaseModel):
    tema: str
    subtemas: List[str]

class TemaQueryRequest(BaseModel):
    tema: str
    subtemas: List[str]

class DocumentoItem(BaseModel):
    id: str
    document: str

class SubtemaDocumentos(BaseModel):
    subtema: str
    documentos: List[DocumentoItem]

class SubtemaQueryRequest(BaseModel):
    subtemas: List[str]