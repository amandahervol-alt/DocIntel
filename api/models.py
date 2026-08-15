from pydantic import BaseModel
from typing import Optional, List

class DocumentInfo(BaseModel):
    """Information about an uploaded document"""
    filename: str
    pages: Optional[int] = None
    word_count: int
    file_size: int
    doc_id: str

class AnalysisRequest(BaseModel):
    """Request for document analysis"""
    doc_ids: List[str]
    context: Optional[str] = None

class SingleDocumentAnalysis(BaseModel):
    """Structured analysis of a single document"""
    executive_summary: str
    key_data_points: List[str]
    action_items: List[str]
    risks_and_gaps: List[str]
    critical_quotes: List[str]

class CrossDocumentAnalysis(BaseModel):
    """Cross-document comparison analysis"""
    common_themes: List[str]
    key_differences: List[str]
    patterns_and_trends: List[str]
    synthesis: str

class AnalysisResponse(BaseModel):
    """Complete analysis response"""
    documents: List[DocumentInfo]
    analyses: dict  # Maps doc_id to SingleDocumentAnalysis
    cross_document_analysis: Optional[CrossDocumentAnalysis] = None
    context_used: Optional[str] = None

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
