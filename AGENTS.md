# DocIntel — AI Orchestration Guide
AGENTS.md — Antigravity Orchestration Architecture

DocIntel is an AI-powered document intelligence and comparative synthesis engine that processes multi-format documents (PDF, DOCX, TXT) and outputs structured insights.

## Architecture Layers

### Layer 1: Document Processing (`core/documents.py`)
- Ingests PDF (`PyMuPDF`), Word (`python-docx`), and plain text.
- Extracts clean textual content and stores document metadata in session memory.
- Manages cross-platform safe temp storage in `.tmp/docintel_uploads`.

### Layer 2: Analysis & Comparison (`core/analysis.py` & `core/comparison.py`)
- **Single Document Analysis**: Formats prompts for Claude to produce 5 core sections:
  1. Executive Summary
  2. Key Data Points & Statistics
  3. Action Items & Recommendations
  4. Risks & Gaps
  5. Critical Quotes & Passages
- **Multi-Document Comparison**: Synthesizes 2+ documents:
  1. Common Themes
  2. Key Differences
  3. Patterns & Trends
  4. Synthesis
- **Zero-Config Offline Fallback**: Generates structured heuristic analyses if no Anthropic API key is provided.

### Layer 3: API & Web Interface (`api/` & `static/`)
- FastAPI endpoints for upload, analysis, listing, and deletion.
- Clean client interface with drag-and-drop file upload, real-time progress indicators, and Markdown/TXT export options.

## Operating Principles
- **Never Truncate Data**: Ensure full document text is analyzed while managing token limits.
- **Strict Structured Outputs**: All responses must parse cleanly into predefined section dictionaries.
- **Cross-Platform Compatibility**: Use platform-agnostic file paths.
