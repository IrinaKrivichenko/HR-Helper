"""
Fuzzy boundary extraction with initial reasoning.
Simple approach with boundary matching.
"""
import time
from typing import Dict, Any, List, Tuple, Optional, Literal
from difflib import SequenceMatcher
from pydantic import BaseModel, Field
from src.logger import logger

class SectionBoundary(BaseModel):
    section: Literal["header", "summary", "skills", "experience", "education"]
    found: bool = Field(
        description="True if this section exists in the resume, False otherwise"
    )
    start: str = Field(
        description="EXACT first 10-15 words of the section as they appear in resume. Empty string '' if section not found"
    )

class BoundaryMarkersSchema(BaseModel):
    overall_reasoning: str = Field(
        description="Your analysis of how this resume is organized and where section boundaries are"
    )
    header: SectionBoundary = Field(
        description="Boundaries of header section containing name, email, phone, LinkedIn, GitHub, location"
    )
    summary: SectionBoundary = Field(
        description="Boundaries of professional summary or objective statement if present"
    )
    skills: SectionBoundary = Field(
        description="Boundaries of skills section with technical skills, tools, programming languages"
    )
    experience: SectionBoundary = Field(
        description="Boundaries of work experience section with jobs, projects, internships"
    )
    education: SectionBoundary = Field(
        description="Boundaries of education section with degrees, certifications, courses, academic publications"
    )


def extract_fuzzy_boundaries(cv_text: str, llm_handler: Any, model: str) -> Dict[str, Any]:
    """
    Extracts sections from the resume using only start markers.
    Validates the result and returns sections, positions, and validation issues.
    """
    start_time = time.time()
    prompt = [
        {
            "role": "system",
            "content": (
                "Identify section boundaries in the resume.\n"
                "Rules:\n"
                "1. FIRST provide overall_reasoning - your thoughts on how sections are organized\n"
                "2. For each standard section, set found=true if it exists, found=false if not\n"
                "3. If section not found, set start to empty string ''\n"
                "4. If section found, provide EXACT first 10-15 words as they appear\n"
            )
        },
        {
            "role": "user",
            "content": f"Analyze and find section boundaries in this resume:\n\n{cv_text}"
        }
    ]
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max(len(cv_text) * 2, 10000),
        response_format=BoundaryMarkersSchema
    )
    markers = response['parsed']
    usage = response.get('usage')
    cost_info = response.get('cost', {})

    # Collect sections with their start positions
    section_starts = []
    issues = []

    # Required sections: header, skills, experience
    required_sections = ["Header", "Skills", "Experience"]

    for field in ['header', 'summary', 'skills', 'experience', 'education']:
        boundary = getattr(markers, field)
        section_name = field.capitalize()  # Приводим к заглавной букве
        if boundary.found and boundary.start:
            start_pos = fuzzy_find(cv_text, boundary.start, threshold=0.75)
            if start_pos is not None:
                section_starts.append((section_name, start_pos))
            else:
                issues.append(f"Section '{section_name}' start marker not found in text!")
                if section_name in required_sections:
                    issues.append(f"Required section '{section_name}' is missing!")
        elif section_name in required_sections:
            issues.append(f"Required section '{section_name}' not found by LLM!")

    # Sort sections by their start position
    section_starts.sort(key=lambda x: x[1])

    # Extract sections: end of current section = start of next section
    sections = {}
    section_positions = {}
    for i in range(len(section_starts)):
        section_name, start_pos = section_starts[i]
        if i < len(section_starts) - 1:
            end_pos = section_starts[i + 1][1]  # Start of next section
        else:
            end_pos = len(cv_text)  # End of document

        section_text = cv_text[start_pos:end_pos].strip()
        sections[section_name] = section_text
        section_positions[section_name] = (start_pos, end_pos)

    # Validate the extraction
    validation = validate_fuzzy_boundaries_extraction(
        original_text=cv_text,
        sections=sections,
        section_positions=section_positions,
        required_sections=["Header", "Skills", "Experience"]
    )

    return {
        "sections": sections,
        "section_positions": section_positions,
        "issues": issues + validation["issues"],
        "validation": validation,
        "reasoning": markers.overall_reasoning,
        "method": "fuzzy_start_only",
        "cost": cost_info.get('total_cost', 0),
        "token_usage": {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
        },
        "time": time.time() - start_time
    }


def fuzzy_find(text: str, marker: str, threshold: float, search_from: int = 0) -> Optional[int]:
    """Find approximate position of marker in text."""
    if not marker:
        return None

    marker_words = marker.lower().split()
    text_lower = text.lower()
    text_words = text_lower.split()

    best_pos = None
    best_score = 0

    window_size = len(marker_words)
    for i in range(search_from, len(text_words) - window_size + 1):
        window = ' '.join(text_words[i:i + window_size])
        score = SequenceMatcher(None, ' '.join(marker_words), window).ratio()

        if score > best_score and score >= threshold:
            best_score = score
            best_pos = text_lower.find(text_words[i], search_from)

    return best_pos


def validate_fuzzy_boundaries_extraction(
    original_text: str,
    sections: Dict[str, str],
    section_positions: Dict[str, Tuple[int, int]],
    required_sections: List[str] = ["Header", "Skills", "Experience"]
) -> Dict[str, Any]:
    """
    Validates extracted sections.
    Returns validation results, including missing required sections.
    """
    if not sections:
        return {
            "is_valid": False,
            "method": "fuzzy_start_only",
            "issues": ["No sections extracted"],
            "metrics": {
                "sections_found": 0,
                "missing_required_sections": required_sections
            },
            "summary": "Failed: no sections found"
        }

    # Check for missing required sections
    missing_sections = [s for s in required_sections if s not in sections]
    issues = []

    if missing_sections:
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")

    # Check for empty sections
    empty_sections = [name for name, text in sections.items() if not text.strip()]
    if empty_sections:
        issues.append(f"Empty sections: {', '.join(empty_sections)}")

    # Generate summary
    if missing_sections:
        summary = f"Failed: missing required sections {', '.join(missing_sections)}"
    elif empty_sections:
        summary = f"Failed: empty sections {', '.join(empty_sections)}"
    else:
        summary = "All required sections are present and non-empty"

    return {
        "is_valid": not missing_sections,
        "method": "fuzzy_start_only",
        "issues": issues,
        "metrics": {
            "sections_found": len(sections),
            "missing_required_sections": missing_sections
        },
        "summary": summary
    }


