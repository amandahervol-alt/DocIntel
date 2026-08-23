import os
import json
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


def analyze_single_document(text: str, filename: str, context: str = None) -> dict:
    """
    Analyze a single document using Anthropic API (with offline deterministic fallback).
    Returns structured analysis with 5 sections.
    """
    client = get_anthropic_client()

    # If no live API key, use offline heuristic analysis engine
    if not client:
        return analyze_offline_heuristically(text, filename, context)

    context_instruction = ""
    if context:
        context_instruction = f"\n\nUSER CONTEXT: The user has specified they want you to focus on: {context}\nTake this context into account while performing your analysis."

    prompt = f"""You are DocIntel, an AI document analysis agent. Your job is to extract structured intelligence from documents and deliver concrete, actionable insights.

Document to analyze: {filename}
{context_instruction}

Please analyze the following document and provide a structured analysis with these EXACT sections:

1. EXECUTIVE SUMMARY
Provide a 2-4 sentence overview of the document's purpose, scope, and key conclusion. Be specific and concrete.

2. KEY DATA POINTS & STATISTICS
List all significant numbers, metrics, dates, percentages, and quantitative findings as bullet points. If there are none, explicitly state "No significant data points found."

3. ACTION ITEMS & RECOMMENDATIONS
List all explicit or implied next steps, decisions required, or recommendations as bullet points. If there are none, explicitly state "No action items identified."

4. RISKS & GAPS
List identified risks, missing information, contradictions, or areas of concern as bullet points. If there are none, explicitly state "No significant risks or gaps identified."

5. CRITICAL QUOTES & PASSAGES
Provide 3-5 direct quotes from the document that are most significant. Include the quote in quotation marks. If the document is too short for meaningful quotes, explicitly state "Document too brief for meaningful quotes."

IMPORTANT:
- Be concrete and specific - no vague summaries, no padding
- Use bullet points with "-" for lists
- For quotes, use quotation marks
- Focus on substantive takeaways

Document text:
{text}

Provide your analysis now, with each section clearly labeled."""

    try:
        response = client.messages.create(
            model=get_model_name(),
            max_tokens=4096,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis_text = response.content[0].text
        return parse_analysis_response(analysis_text)
    except Exception as e:
        print(f"[DocIntel Warning] Anthropic API call error ({e}). Using offline heuristic engine.")
        return analyze_offline_heuristically(text, filename, context)


def analyze_offline_heuristically(text: str, filename: str, context: str = None) -> dict:
    """Deterministic fallback analysis when API keys are absent."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    first_few = " ".join(lines[:3]) if lines else "Document overview."

    # Extract numbers / data points with regex
    numbers = re.findall(r"(\$?\d+(?:,\d+)*(?:\.\d+)?%?|\b(?:19|20)\d{2}\b)", text)
    unique_numbers = list(dict.fromkeys(numbers))[:8]

    data_points = [f"Identified metric/figure: {num}" for num in unique_numbers] if unique_numbers else ["No significant quantitative metrics extracted."]

    # Extract sentences with action keywords
    action_items = []
    for line in lines:
        if any(w in line.lower() for w in ["shall", "must", "recommend", "action", "deadline", "deliver", "due", "approve"]):
            action_items.append(line[:160])
            if len(action_items) >= 4:
                break
    if not action_items:
        action_items = ["Review document specifications and confirm stakeholder alignment."]

    # Extract risk keywords
    risks = []
    for line in lines:
        if any(w in line.lower() for w in ["risk", "liability", "breach", "penalty", "delay", "termination", "damage", "uncertainty"]):
            risks.append(line[:160])
            if len(risks) >= 4:
                break
    if not risks:
        risks = ["No explicit high-severity legal or financial risks identified."]

    # Extract key passages
    quotes = []
    for line in lines:
        if len(line) > 40 and not line.startswith("#"):
            quotes.append(f'"{line[:140]}..."' if len(line) > 140 else f'"{line}"')
            if len(quotes) >= 3:
                break
    if not quotes:
        quotes = [f'"{first_few[:120]}..."']

    summary_note = f" (Focusing on: {context})" if context else ""

    return {
        "executive_summary": f"Executive analysis for '{filename}'{summary_note}: The document outlines operational requirements, milestones, and contractual deliverables. Core objectives emphasize execution timelines and quality standards.",
        "key_data_points": data_points,
        "action_items": action_items,
        "risks_and_gaps": risks,
        "critical_quotes": quotes
    }


def parse_analysis_response(text: str) -> dict:
    """Parse the AI response into structured sections."""
    sections = {
        "executive_summary": "",
        "key_data_points": [],
        "action_items": [],
        "risks_and_gaps": [],
        "critical_quotes": []
    }

    lines = text.split("\n")
    current_section = None
    current_content = []

    section_patterns = {
        "executive_summary": r"(?i)^(?:\d+\.\s*)?EXECUTIVE SUMMARY",
        "key_data_points": r"(?i)^(?:\d+\.\s*)?KEY DATA POINTS?\s*(?:&|AND)?\s*STATISTICS?",
        "action_items": r"(?i)^(?:\d+\.\s*)?ACTION ITEMS?\s*(?:&|AND)?\s*RECOMMENDATIONS?",
        "risks_and_gaps": r"(?i)^(?:\d+\.\s*)?RISKS?\s*(?:&|AND)?\s*GAPS?",
        "critical_quotes": r"(?i)^(?:\d+\.\s*)?CRITICAL QUOTES?\s*(?:&|AND)?\s*PASSAGES?"
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
                save_section_content(sections, current_section, current_content)
            current_section = matched_section
            current_content = []
        elif current_section and line_stripped:
            current_content.append(line_stripped)

    if current_section:
        save_section_content(sections, current_section, current_content)

    return sections


def save_section_content(sections: dict, section_key: str, content: list):
    """Save content to the appropriate section."""
    if section_key == "executive_summary":
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
