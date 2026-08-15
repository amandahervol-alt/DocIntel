from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import List
from api.models import DocumentInfo, AnalysisRequest, AnalysisResponse, ErrorResponse
from core.documents import DocumentProcessor, get_document, documents_store
from core.analysis import analyze_single_document
from core.comparison import compare_documents

router = APIRouter()

@router.post("/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, or TXT)
    Returns document info including ID, filename, page count, and word count
    """
    try:
        doc_info = await DocumentProcessor.process_upload(file)
        return doc_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during upload: {str(e)}"
        )

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_documents(request: AnalysisRequest):
    """
    Analyze one or more documents
    Returns structured analysis with optional cross-document comparison
    """
    if not request.doc_ids:
        raise HTTPException(status_code=400, detail="No documents provided for analysis")
    
    # Retrieve all documents
    documents = []
    for doc_id in request.doc_ids:
        doc = get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        documents.append(doc)
    
    try:
        # Analyze each document individually
        analyses = {}
        for doc in documents:
            analysis = analyze_single_document(
                text=doc["text"],
                filename=doc["filename"],
                context=request.context
            )
            analyses[doc["doc_id"]] = analysis
        
        # If multiple documents, perform cross-document comparison
        cross_doc_analysis = None
        if len(documents) > 1:
            doc_list = [
                {"filename": doc["filename"], "text": doc["text"]}
                for doc in documents
            ]
            cross_doc_analysis = compare_documents(doc_list, context=request.context)
        
        # Build response
        doc_infos = [
            DocumentInfo(
                filename=doc["filename"],
                pages=doc.get("pages"),
                word_count=doc["word_count"],
                file_size=doc["file_size"],
                doc_id=doc["doc_id"]
            )
            for doc in documents
        ]
        
        response = AnalysisResponse(
            documents=doc_infos,
            analyses=analyses,
            cross_document_analysis=cross_doc_analysis,
            context_used=request.context
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during analysis: {str(e)}"
        )

@router.get("/documents")
async def list_documents():
    """
    List all uploaded documents in current session
    """
    doc_list = [
        {
            "doc_id": doc_id,
            "filename": doc["filename"],
            "pages": doc.get("pages"),
            "word_count": doc["word_count"],
            "file_size": doc["file_size"]
        }
        for doc_id, doc in documents_store.items()
    ]
    return {"documents": doc_list}

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document from the session
    """
    from core.documents import cleanup_document
    
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    
    cleanup_document(doc_id)
    return {"message": "Document deleted successfully"}

@router.delete("/documents")
async def clear_all_documents():
    """
    Clear all documents from the session
    """
    from core.documents import cleanup_document
    
    doc_ids = list(documents_store.keys())
    for doc_id in doc_ids:
        cleanup_document(doc_id)
    
    return {"message": f"Cleared {len(doc_ids)} documents"}
