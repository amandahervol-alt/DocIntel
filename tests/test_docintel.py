import os
import io
import pytest
from fastapi.testclient import TestClient
from main import app
from core.analysis import analyze_single_document
from core.comparison import compare_documents
from core.documents import DocumentProcessor, documents_store, cleanup_document

client = TestClient(app)


def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "DocIntel" in response.text


def test_upload_and_analyze_txt():
    # 1. Test Upload
    sample_content = (
        "Project Alpha Statement of Work:\n"
        "Delivery Deadline: December 31, 2026. Total Project Budget: $250,000.00.\n"
        "Contractor shall deliver milestones on schedule. Penalties apply for delayed handoff."
    )
    file_bytes = io.BytesIO(sample_content.encode("utf-8"))

    upload_res = client.post(
        "/api/upload",
        files={"file": ("project_alpha_sow.txt", file_bytes, "text/plain")}
    )
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    assert "doc_id" in doc_data
    assert doc_data["word_count"] > 10
    doc_id = doc_data["doc_id"]

    # 2. Test Listing
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    assert any(d["doc_id"] == doc_id for d in list_res.json()["documents"])

    # 3. Test Single Analysis
    analyze_res = client.post(
        "/api/analyze",
        json={"doc_ids": [doc_id], "context": "Focus on delivery deadlines and budget"}
    )
    assert analyze_res.status_code == 200
    analysis_data = analyze_res.json()
    assert doc_id in analysis_data["analyses"]
    doc_analysis = analysis_data["analyses"][doc_id]
    assert "executive_summary" in doc_analysis
    assert "key_data_points" in doc_analysis
    assert "action_items" in doc_analysis
    assert "risks_and_gaps" in doc_analysis
    assert "critical_quotes" in doc_analysis

    # 4. Clean up
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200


def test_multi_document_comparison():
    # Upload Document 1
    f1 = io.BytesIO(b"Document 1: Cloud Uptime Agreement. SLA target is 99.95%. Payment $14,500/month.")
    res1 = client.post("/api/upload", files={"file": ("sla.txt", f1, "text/plain")})
    id1 = res1.json()["doc_id"]

    # Upload Document 2
    f2 = io.BytesIO(b"Document 2: Q4 Performance Report. Delivered 99.98% uptime. Cloud fees $14,500/month.")
    res2 = client.post("/api/upload", files={"file": ("report.txt", f2, "text/plain")})
    id2 = res2.json()["doc_id"]

    # Run Cross-Document Analysis
    analyze_res = client.post(
        "/api/analyze",
        json={"doc_ids": [id1, id2], "context": "Compare SLA targets against actual performance"}
    )
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["cross_document_analysis"] is not None
    cross = data["cross_document_analysis"]
    assert "common_themes" in cross
    assert "key_differences" in cross
    assert "patterns_and_trends" in cross
    assert "synthesis" in cross

    # Clear all documents
    clear_res = client.delete("/api/documents")
    assert clear_res.status_code == 200
