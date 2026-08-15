import os
from anthropic import Anthropic
from fastapi import HTTPException
import json
import re

MODEL_NAME = "claude-sonnet-4-20250514"

def get_anthropic_client():
    """Get or create Anthropic client"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not found in environment variables"
        )
    return Anthropic(api_key=api_key)

def analyze_single_document(text: str, filename: str, context: str = None) -> dict:
    """
    Analyze a single document using Anthropic API
    Returns structured analysis with 5 sections
    """
    
    # Build the prompt
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
- Be concrete and specific - no vague summaries, no padding, no generic observations
- Use bullet points with "-" for lists
- For quotes, use quotation marks
- If a section has nothing meaningful to report, say so explicitly rather than leaving it blank or being vague
- Focus on what matters, not what sounds impressive

Document text:
{text}

Provide your analysis now, with each section clearly labeled."""

    try:
        client = get_anthropic_client()
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        analysis_text = response.content[0].text
        
        # Parse the response into structured sections
        parsed_analysis = parse_analysis_response(analysis_text)
        
        return parsed_analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze document with AI: {str(e)}"
        )

def parse_analysis_response(text: str) -> dict:
    """
    Parse the AI response into structured sections
    """
    sections = {
        "executive_summary": "",
        "key_data_points": [],
        "action_items": [],
        "risks_and_gaps": [],
        "critical_quotes": []
    }
    
    # Split by section headers (case insensitive)
    lines = text.split('\n')
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
        
        # Check if this line is a section header
        matched_section = None
        for section_key, pattern in section_patterns.items():
            if re.match(pattern, line_stripped):
                matched_section = section_key
                break
        
        if matched_section:
            # Save previous section content
            if current_section:
                save_section_content(sections, current_section, current_content)
            
            # Start new section
            current_section = matched_section
            current_content = []
        elif current_section and line_stripped:
            current_content.append(line_stripped)
    
    # Save the last section
    if current_section:
        save_section_content(sections, current_section, current_content)
    
    return sections

def save_section_content(sections: dict, section_key: str, content: list):
    """
    Save content to the appropriate section
    """
    if section_key == "executive_summary":
        # Join all lines for executive summary
        sections[section_key] = " ".join(content).strip()
    else:
        # For list sections, extract bullet points
        items = []
        for line in content:
            # Check if it's a bullet point
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                items.append(line.lstrip('-•* ').strip())
            elif line and not re.match(r'^(?i)(no\s+|none)', line):
                # If it's not empty and not a "no items" statement, add it
                # But first check if previous line was incomplete
                if items and not items[-1].endswith('.') and not items[-1].endswith('"'):
                    items[-1] += " " + line
                else:
                    items.append(line)
        
        # If no items found, check if there's a statement like "No items found"
        if not items and content:
            full_text = " ".join(content).strip()
            if full_text:
                items.append(full_text)
        
        sections[section_key] = items
