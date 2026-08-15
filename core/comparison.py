import os
from anthropic import Anthropic
from fastapi import HTTPException
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

def compare_documents(documents: list, context: str = None) -> dict:
    """
    Perform cross-document comparison analysis
    Returns structured comparison with 4 components
    
    Args:
        documents: List of dicts with 'filename' and 'text' keys
        context: Optional user context to guide analysis
    """
    
    # Build document texts for the prompt
    doc_texts = []
    for i, doc in enumerate(documents, 1):
        doc_texts.append(f"DOCUMENT {i}: {doc['filename']}\n{doc['text']}\n")
    
    combined_docs = "\n" + "="*80 + "\n".join(doc_texts)
    
    # Build context instruction
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
- If documents don't have meaningful commonalities or differences, say so explicitly
- Focus on substantive insights, not surface-level observations
- The synthesis should tie everything together into a coherent takeaway

Documents to compare:
{combined_docs}

Provide your cross-document analysis now, with each section clearly labeled."""

    try:
        client = get_anthropic_client()
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        comparison_text = response.content[0].text
        
        # Parse the response into structured sections
        parsed_comparison = parse_comparison_response(comparison_text)
        
        return parsed_comparison
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform cross-document comparison: {str(e)}"
        )

def parse_comparison_response(text: str) -> dict:
    """
    Parse the AI comparison response into structured sections
    """
    sections = {
        "common_themes": [],
        "key_differences": [],
        "patterns_and_trends": [],
        "synthesis": ""
    }
    
    lines = text.split('\n')
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
        
        # Check if this line is a section header
        matched_section = None
        for section_key, pattern in section_patterns.items():
            if re.match(pattern, line_stripped):
                matched_section = section_key
                break
        
        if matched_section:
            # Save previous section content
            if current_section:
                save_comparison_section(sections, current_section, current_content)
            
            # Start new section
            current_section = matched_section
            current_content = []
        elif current_section and line_stripped:
            current_content.append(line_stripped)
    
    # Save the last section
    if current_section:
        save_comparison_section(sections, current_section, current_content)
    
    return sections

def save_comparison_section(sections: dict, section_key: str, content: list):
    """
    Save content to the appropriate comparison section
    """
    if section_key == "synthesis":
        # Join all lines for synthesis
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
                if items and not items[-1].endswith('.') and not items[-1].endswith('"'):
                    items[-1] += " " + line
                else:
                    items.append(line)
        
        # If no items found, check if there's a statement
        if not items and content:
            full_text = " ".join(content).strip()
            if full_text:
                items.append(full_text)
        
        sections[section_key] = items
