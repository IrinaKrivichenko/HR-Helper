from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field
from typing import List, Optional

from src.data_processing.nlp.llm_handler import LLMHandler


class SectionExtraction(BaseModel):
    reasoning: List[str] = Field(description="Step-by-step reasoning for section extraction")
    content: str = Field(description="Extracted content of the section")


# Required sections for extraction
MANDATORY_SECTIONS = ["Header", "Skills", "Experience"]


def extract_single_section(
    cv_text: str,
    section_name: str,
    llm_handler: LLMHandler,
    model: str
) -> Dict[str, Any]:
    """
    Extracts a single section from the resume text.
    Returns the extracted section, reasoning, cost, and token usage.
    """
    prompt = f"""
    Find and extract the ENTIRE '{section_name}' section from this resume.
    Consider that the text may be broken or mixed with other sections.
    If the section does not exist, return an empty string.
    ---
    {cv_text}
    """
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max(len(cv_text) * 3, 1000),
        response_format=SectionExtraction
    )

    content = response.get("content", "").strip()
    reasoning = response.get("reasoning", "")
    usage = response.get("usage", {})
    cost_info = response.get("cost", {})

    return {
        "content": content,
        "reasoning": reasoning,
        "cost": cost_info.get("total_cost", 0),
        "token_usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0)
        }
    }

def extract_section_by_section(
    cv_text: str,
    llm_handler: LLMHandler,
    model: str,
    existing_sections: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Extracts only missing sections from the resume text.
    Returns a structured result with sections, reasoning, validation, cost, and token usage.
    """
    if existing_sections is None:
        existing_sections = {}

    start_time = time.time()
    sections = existing_sections.copy()
    all_reasoning = []
    total_cost = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # Determine which sections are missing
    missing_sections = [section for section in MANDATORY_SECTIONS if section not in sections or not sections[section]]

    # Extract only missing sections
    for section in missing_sections:
        result = extract_single_section(cv_text, section, llm_handler, model)
        content = result["content"]

        # If section is empty, replace with full resume text
        if not content:
            content = cv_text

        sections[section] = content
        all_reasoning.append(f"{section} reasoning: {result['reasoning']}")
        total_cost += result["cost"]
        total_prompt_tokens += result["token_usage"]["prompt_tokens"]
        total_completion_tokens += result["token_usage"]["completion_tokens"]

    # Validate that all required sections are non-empty
    validation = {
        "is_valid": all(sections[section] for section in MANDATORY_SECTIONS),
        "method": "section_by_section",
        "issues": [f"Section '{section}' is empty" for section in MANDATORY_SECTIONS if not sections[section]],
        "metrics": {
            "sections_found": len(sections),
            "empty_sections": [section for section in MANDATORY_SECTIONS if not sections[section]]
        },
        "summary": "All sections extracted successfully" if all(sections[section] for section in MANDATORY_SECTIONS) else "Some sections are empty"
    }

    return {
        "sections": sections,
        "reasoning": "\n\n".join(all_reasoning),
        "validation": validation,
        "method": "section_by_section",
        "cost": total_cost,
        "token_usage": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens
        },
        "time": time.time() - start_time
    }
