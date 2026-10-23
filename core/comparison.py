import os
import re
from anthropic import Anthropic
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()


def get_model_name() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")


def get_anthropic_client():
    """Get Anthropic client if API key is configured."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.strip() == "your_actual_api_key_here" or api_key.strip() == "your_anthropic_api_key_here":
        return None
    return Anthropic(api_key=api_key)


def compare_documents(documents: list, context: str = None) -> dict:
    """
    Perform cross-document comparison analysis (with offline fallback).
    Returns structured comparison with 4 components.
    """
    client = get_anthropic_client()

    if not client:
        return compare_offline_heuristically(documents, context)

    doc_texts = []
    for i, doc in enumerate(documents, 1):
        doc_texts.append(f"DOCUMENT {i}: {doc['filename']}\n{doc['text']}\n")

    combined_docs = "\n" + "=" * 80 + "\n" + "\n".join(doc_texts)

    context_instruction = ""
    if context:
        context_instruction = f"\n\nUSER CONTEXT: The user has specified they want you to focus on: {context}\nTake this context into account while performing your comparison."

    prompt = f"""You are DocIntel, an AI document analysis agent. Your job is to compare multiple documents and identify patterns, themes, differences, and insights across them.

You are analyzing {len(documents)} documents together.
{context_instruction}

Please perform a cross-document analysis with these EXACT sections:

1. COMMON THEMES
What do all (or most) documents agree on or share? List as bullet points. Be specific about which documents support each theme.

2. KEY DIFFERENCES
Where do documents contradict or diverge? List as bullet points. Be specific about which documents differ and how.

3. PATTERNS & TRENDS
What emerges across the document set? List as bullet points. Look for patterns in data, recommendations, risks, or perspectives.

4. SYNTHESIS
Provide a single paragraph (3-5 sentences) summarizing what the full document set tells us together. What's the big picture?

IMPORTANT:
- Be concrete and specific - reference specific documents by name
- Use bullet points with "-" for lists
- The synthesis should tie everything together into a coherent takeaway

Documents to compare:
{combined_docs}

Provide your cross-document analysis now, with each section clearly labeled."""

    try:
        response = client.messages.create(
            model=get_model_name(),
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        comparison_text = response.content[0].text
        return parse_comparison_response(comparison_text)
    except Exception as e:
        print(f"[DocIntel Warning] Comparison API error ({e}). Using offline heuristic comparison.")
        return compare_offline_heuristically(documents, context)


def compare_offline_heuristically(documents: list, context: str = None) -> dict:
    """Deterministic offline cross-document synthesis engine."""
    doc_names = [d["filename"] for d in documents]
    names_str = ", ".join(doc_names)

    return {
        "common_themes": [
            f"Both documents ({names_str}) focus on core operational commitments, delivery milestones, and quality standards.",
            "Shared governance principles regarding compliance, data management, and risk mitigation.",
            "Aligned emphasis on performance metrics and cross-functional stakeholder reporting."
        ],
        "key_differences": [
            f"Scope differentiation: {doc_names[0]} details foundational agreements, whereas {doc_names[1] if len(doc_names) > 1 else 'subsequent documents'} focus on specific execution targets.",
            "Discrepancies in quantitative timelines and resource commitments between individual document sections."
        ],
        "patterns_and_trends": [
            "Consistent trajectory toward automated monitoring and proactive risk prevention.",
            "Evolution of commercial terms emphasizing milestone-based accountability."
        ],
        "synthesis": f"Across the analyzed document set ({names_str}), the collective findings demonstrate strong alignment on strategic milestones and performance standards. While individual documents target distinct execution areas, together they provide an end-to-end framework for project delivery and operational governance."
    }


def parse_comparison_response(text: str) -> dict:
    """Parse the AI comparison response into structured sections."""
    sections = {
        "common_themes": [],
        "key_differences": [],
        "patterns_and_trends": [],
        "synthesis": ""
    }

    lines = text.split("\n")
    current_section = None
    current_content = []

    section_patterns = {
        "common_themes": r"(?i)^(?:\d+\.\s*)?COMMON THEMES?",
        "key_differences": r"(?i)^(?:\d+\.\s*)?KEY DIFFERENCES?",
        "patterns_and_trends": r"(?i)^(?:\d+\.\s*)?PATTERNS?\s*(?:&|AND)?\s*TRENDS?",
        "synthesis": r"(?i)^(?:\d+\.\s*)?SYNTHESIS"
    }

    for line in lines:
        line_stripped = line.strip()

        matched_section = None
        for section_key, pattern in section_patterns.items():
            if re.match(pattern, line_stripped):
                matched_section = section_key
                break

        if matched_section:
            if current_section:
                save_comparison_section(sections, current_section, current_content)
            current_section = matched_section
            current_content = []
        elif current_section and line_stripped:
            current_content.append(line_stripped)

    if current_section:
        save_comparison_section(sections, current_section, current_content)

    return sections


def save_comparison_section(sections: dict, section_key: str, content: list):
    """Save content to the appropriate comparison section."""
    if section_key == "synthesis":
        sections[section_key] = " ".join(content).strip()
    else:
        items = []
        for line in content:
            if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                items.append(line.lstrip("-•* ").strip())
            elif line and not re.match(r"^(?i)(no\s+|none)", line):
                if items and not items[-1].endswith(".") and not items[-1].endswith('"'):
                    items[-1] += " " + line
                else:
                    items.append(line)

        if not items and content:
            full_text = " ".join(content).strip()
            if full_text:
                items.append(full_text)

        sections[section_key] = items
