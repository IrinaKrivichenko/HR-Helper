"""
Main section identification module.
"""
import time
import re
from typing import Dict, Any, Literal
from .full_extraction import extract_full_sections, validate_full_sections_extraction
from .fuzzy_boundaries import extract_fuzzy_boundaries, validate_fuzzy_boundaries_extraction
from src.logger import logger


# Method configuration dictionary
METHODS = {
    "full": {
        "extraction_function": extract_full_sections,
        "validation_function": validate_full_sections_extraction
    },
    "fuzzy": {
        "extraction_function": extract_fuzzy_boundaries,
        "validation_function": validate_fuzzy_boundaries_extraction
    }
}


def identify_resume_sections(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano",
    size_threshold: int = 1000
) -> Dict[str, Any]:
    """
    Identify and extract resume sections.
    Returns flat dictionary with sections and extraction info.
    """
    start_time = time.time()
    cv_length = len(cv_text)
    text_quality = assess_text_quality(cv_text)

    # Initialize tracking
    path_steps = []
    total_cost = 0
    total_tokens = 0
    sections = {}

    # Step 2.1: Choose initial method
    if text_quality == "messy":
        method = "full"
        path_steps.append(f"Step 2.1: Text is messy, starting with full extraction")
    else:
        method = "fuzzy"
        path_steps.append(f"Step 2.1: Text is clean, starting with fuzzy boundaries")

    # Step 2.2-2.3: Initial extraction
    extraction_start = time.time()
    extract_func = METHODS[method]["extraction_function"]
    result = extract_func(cv_text, llm_handler, model)
    extraction_time = time.time() - extraction_start

    path_steps.append(f"Step 2.2: {result.get('reasoning', 'Analyzing resume structure')}")
    path_steps.append(f"Step 2.3: Initial {method} extraction completed in {extraction_time:.2f} sec, found {len(result['sections'])} sections")

    sections = result["sections"]
    total_cost += result.get("cost", 0)
    total_tokens += result.get("token_usage", {}).get("prompt_tokens", 0)
    total_tokens += result.get("token_usage", {}).get("completion_tokens", 0)

    # Check validation result from extraction
    if result["validation"]["is_valid"]:
        path_steps.append(f"Step 2.4: {method} validation PASSED - {result['validation']['summary']}")
    else:
        # Validation failed
        issues = " | ".join(result["validation"]["issues"][:2])
        path_steps.append(f"Step 2.4: {method} validation FAILED - {issues}")

        # Step 2.5: Try alternative method
        if method == "full":
            alternative_method = "fuzzy"
        else:
            alternative_method = "full"

        path_steps.append(f"Step 2.5: Trying alternative method: {alternative_method}")

        alternative_extract = METHODS[alternative_method]["extraction_function"]
        alternative_start = time.time()
        alternative_result = alternative_extract(cv_text, llm_handler, model)
        alternative_time = time.time() - alternative_start

        path_steps.append(f"Step 2.6: Alternative {alternative_method} extraction completed in {alternative_time:.2f} sec")

        if alternative_result["validation"]["is_valid"]:
            path_steps.append(f"Step 2.7: Alternative {alternative_method} validation PASSED - {alternative_result['validation']['summary']}")
            sections = alternative_result["sections"]
            total_cost += alternative_result.get("cost", 0)
            total_tokens += alternative_result.get("token_usage", {}).get("prompt_tokens", 0)
            total_tokens += alternative_result.get("token_usage", {}).get("completion_tokens", 0)
        else:
            # Both methods failed, use section_by_section for missing sections
            path_steps.append(f"Step 2.7: Both methods failed, using section_by_section for missing sections")

            from .section_by_section import extract_section_by_section
            fallback_start = time.time()
            fallback_result = extract_section_by_section(cv_text, llm_handler, model, sections)
            fallback_time = time.time() - fallback_start

            sections = fallback_result["sections"]
            total_cost += fallback_result.get("cost", 0)
            total_tokens += fallback_result.get("token_usage", {}).get("prompt_tokens", 0)
            total_tokens += fallback_result.get("token_usage", {}).get("completion_tokens", 0)

            path_steps.append(f"Step 2.8: Section-by-section fallback completed in {fallback_time:.2f} sec")

    # Build final result
    final_result = {}
    # Add all sections (flat structure)
    for section_name, content in sections.items():
        final_result[section_name] = content

    # Add metadata with correct naming
    final_result["Step 2 Total Section Extraction time"] = time.time() - start_time
    final_result["Section Extraction Model"] = model
    final_result["Total Section Extraction tokens"] = total_tokens
    final_result["Total Section Extraction cost"] = total_cost
    final_result["Section Extraction Path"] = "\n".join(path_steps)

    logger.info(f"Section identification completed in {final_result['Step 2 Total Section Extraction time']:.2f}s")
    return final_result



def assess_text_quality(text: str) -> Literal["clean", "messy"]:
    """
    Quick check if text has parsing issues.
    """
    if not text:
        return "messy"

    # Check for common PDF issues
    has_broken_words = bool(re.search(r'\b\w\s+\w\s+\w\s+\w\b', text))
    has_mid_breaks = len(re.findall(r'[a-z]\n[a-z]', text)) > 3
    has_missing_spaces = len(re.findall(r'[a-z][A-Z]', text)) > 5
    has_encoding_issues = bool(re.search(r'[�□◊]+', text))

    return "messy" if any([has_broken_words, has_mid_breaks, has_missing_spaces, has_encoding_issues]) else "clean"
