import fitz  # PyMuPDF
from docx import Document
from typing import Tuple, Optional
import os
import uuid
from fastapi import UploadFile, HTTPException

# Store documents in memory (session-based)
documents_store = {}

# File size limit: 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes

class DocumentProcessor:
    """Handle document upload and text extraction"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF file
        Returns: (text, page_count)
        """
        try:
            doc = fitz.open(file_path)
            text = ""
            page_count = len(doc)
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            return text.strip(), page_count
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """
        Extract text from DOCX file
        Returns: text
        """
        try:
            doc = Document(file_path)
            text = []
            
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            
            return "\n".join(text).strip()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from DOCX: {str(e)}"
            )
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """
        Extract text from TXT file
        Returns: text
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read().strip()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to read text file: {str(e)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read text file: {str(e)}"
            )
    
    @staticmethod
    async def process_upload(file: UploadFile) -> dict:
        """
        Process uploaded file and extract text
        Returns: document info dictionary
        """
        # Validate file type
        filename = file.filename.lower()
        if not (filename.endswith('.pdf') or filename.endswith('.docx') or filename.endswith('.txt')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload PDF, DOCX, or TXT files only."
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        # Create temporary file
        temp_dir = "/tmp/docintel_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        doc_id = str(uuid.uuid4())
        temp_file_path = os.path.join(temp_dir, f"{doc_id}_{file.filename}")
        
        with open(temp_file_path, 'wb') as f:
            f.write(content)
        
        # Extract text based on file type
        try:
            pages = None
            if filename.endswith('.pdf'):
                text, pages = DocumentProcessor.extract_text_from_pdf(temp_file_path)
            elif filename.endswith('.docx'):
                text = DocumentProcessor.extract_text_from_docx(temp_file_path)
            else:  # .txt
                text = DocumentProcessor.extract_text_from_txt(temp_file_path)
            
            # Calculate word count
            word_count = len(text.split())
            
            if not text or word_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The document appears to be empty or contains no extractable text."
                )
            
            # Store document info
            doc_info = {
                "doc_id": doc_id,
                "filename": file.filename,
                "pages": pages,
                "word_count": word_count,
                "file_size": file_size,
                "text": text,
                "temp_path": temp_file_path
            }
            
            documents_store[doc_id] = doc_info
            
            return {
                "doc_id": doc_id,
                "filename": file.filename,
                "pages": pages,
                "word_count": word_count,
                "file_size": file_size
            }
            
        except HTTPException:
            # Clean up temp file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred while processing the document: {str(e)}"
            )

def get_document(doc_id: str) -> Optional[dict]:
    """Get document from store"""
    return documents_store.get(doc_id)

def cleanup_document(doc_id: str):
    """Remove document from store and clean up temp file"""
    if doc_id in documents_store:
        doc_info = documents_store[doc_id]
        temp_path = doc_info.get("temp_path")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        del documents_store[doc_id]
