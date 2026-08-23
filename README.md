# DocIntel 📑

AI-powered document intelligence and comparative synthesis application that delivers structured insights from any document type.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Overview & Capabilities

DocIntel accepts uploaded documents (PDF, DOCX, TXT), extracts their content, and uses structured AI intelligence to deliver concrete, actionable analysis across contracts, research reports, financial statements, proposals, and policy briefs.

### 1. Single Document Analysis (5-Section Intelligence Breakdown)
- **Executive Summary**: High-level synthesis of purpose, scope, and key conclusions.
- **Key Data Points & Statistics**: Quantitative findings, metrics, dates, and percentages.
- **Action Items & Recommendations**: Concrete next steps and decision items.
- **Risks & Gaps**: Identified liabilities, missing information, and areas of concern.
- **Critical Quotes & Passages**: Significant direct passages extracted with context.

### 2. Multi-Document Comparative Synthesis (2+ Documents)
- **Common Themes**: Core shared objectives and aligned terms across documents.
- **Key Differences**: Structural contradictions and scope variances.
- **Patterns & Trends**: High-level trajectories across the document set.
- **Overarching Synthesis**: Unified executive takeaway.

---

## 🏗️ Tech Stack & Architecture

- **Backend**: Python FastAPI with async non-blocking file processing.
- **Frontend**: Vanilla HTML5, CSS3, and JavaScript with responsive drag-and-drop file upload.
- **AI Engine**: Anthropic Claude (`claude-3-7-sonnet-20250219` / `claude-3-5-sonnet-20241022`) with zero-config offline heuristic fallback.
- **Document Processing**: PyMuPDF (`fitz`) and `pypdf` for PDFs, `python-docx` for Word documents, and multi-encoding text decoding.
- **Export Engine**: Client-side Markdown and plain-text export with formatted timestamps.

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/amandahervol-alt/DocIntel.git
cd DocIntel
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure Live AI API Key
Copy `.env.example` to `.env` to enable live Claude analysis:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219
```
*(If no API key is provided, the application runs seamlessly in zero-config offline analysis mode).*

### 4. Start the Application
```bash
python main.py
```
Open **`http://localhost:8000`** in your browser!

### 5. Run Automated Test Suite
```bash
python -m pytest tests/
```

---

## 📂 Repository Structure

```
DocIntel/
├── data/
│   └── samples/              # Pre-loaded sample document fixtures (SLA, Quarterly Report)
├── api/
│   ├── routes.py             # FastAPI REST endpoints (/upload, /analyze, /documents)
│   └── models.py             # Pydantic request & response models
├── core/
│   ├── documents.py          # Multi-format document parser & cross-platform temp storage
│   ├── analysis.py           # Single document 5-section analysis engine
│   └── comparison.py         # Multi-document cross-comparison engine
├── static/
│   ├── index.html            # Main web UI
│   ├── style.css             # Glassmorphism styling & animations
│   └── app.js                # Frontend client state & export logic
├── tests/
│   └── test_docintel.py      # Pytest automated test suite
├── requirements.txt          # Project dependencies
├── AGENTS.md                 # Antigravity Orchestration Guide
├── LICENSE                   # MIT License
├── .env.example              # Environment variables template
└── README.md
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
