try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

import io
from docx import Document
from typing import Tuple, Optional
import os
import uuid
import tempfile
from fastapi import UploadFile, HTTPException

# Store documents in memory (session-based)
documents_store = {}

# File size limit: 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes


class DocumentProcessor:
    """Handle document upload and text extraction across PDF, DOCX, and TXT files."""

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
        """
        Extract text from PDF file using PyMuPDF (fitz) or pypdf fallback.
        Returns: (text, page_count)
        """
        # Option A: Use PyMuPDF
        if fitz is not None:
            try:
                doc = fitz.open(file_path)
                text = ""
                page_count = len(doc)

                for page in doc:
                    text += page.get_text()

                doc.close()
                return text.strip(), page_count
            except Exception as e:
                pass  # Fall through to pypdf

        # Option B: Use pypdf
        if pypdf is not None:
            try:
                with open(file_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    pages = len(reader.pages)
                    text_parts = []
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_parts.append(page_text.strip())
                    return "\n\n".join(text_parts).strip(), pages
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to extract text from PDF using pypdf: {str(e)}"
                )

        raise HTTPException(
            status_code=500,
            detail="No PDF extraction library (PyMuPDF or pypdf) available on server."
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
                if paragraph.text.strip():
                    text.append(paragraph.text.strip())

            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        text.append(row_text)

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
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1", errors="replace") as f:
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
        if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".txt") or filename.endswith(".md")):
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

        # Create temporary file safely across platforms
        temp_dir = os.path.join(tempfile.gettempdir(), "docintel_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        doc_id = str(uuid.uuid4())[:8]
        temp_file_path = os.path.join(temp_dir, f"{doc_id}_{file.filename}")

        with open(temp_file_path, "wb") as f:
            f.write(content)

        # Extract text based on file type
        try:
            pages = None
            if filename.endswith(".pdf"):
                text, pages = DocumentProcessor.extract_text_from_pdf(temp_file_path)
            elif filename.endswith(".docx"):
                text = DocumentProcessor.extract_text_from_docx(temp_file_path)
            else:
                text = DocumentProcessor.extract_text_from_txt(temp_file_path)

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
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise
        except Exception as e:
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
            try:
                os.remove(temp_path)
            except OSError:
                pass
        del documents_store[doc_id]
