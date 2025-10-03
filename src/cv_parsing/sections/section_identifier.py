"""
Main section identification module.
"""
import time
from typing import Dict, Any, Literal
from .full_extraction import extract_full_sections
from src.logger import logger
from .section_by_section import extract_section_by_section
from ...data_processing.nlp.llm_handler import LLMHandler


def identify_resume_sections(
    cv_text: str,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano",
    size_threshold: int = 1000
) -> Dict[str, Any]:
    """
    Identify and extract resume sections using the full extraction method.
    Falls back to section-by-section extraction for missing mandatory sections.
    """
    start_time = time.time()
    path_steps = []

    # Step 1: Extract sections using the full method
    extraction_start = time.time()
    result = extract_full_sections(cv_text, llm_handler, model)
    extraction_time = time.time() - extraction_start

    path_steps.append(f"Step 1: Full extraction completed in {extraction_time:.2f} sec")
    path_steps.append(f"Reasoning: {result.get('reasoning', 'Analyzing resume structure')}")

    # Initialize fallback_result as None
    fallback_result = None

    # Step 2: Check for missing mandatory sections
    mandatory_sections = ["Header", "Skills", "Experience"]
    missing_sections = [
        section for section in mandatory_sections
        if section not in result["sections"] or not result["sections"][section].strip()
    ]

    if missing_sections:
        path_steps.append(f"Step 2: Missing mandatory sections detected: {', '.join(missing_sections)}")
        path_steps.append("Step 3: Falling back to section-by-section extraction for missing sections")

        # Step 4: Extract only missing sections
        fallback_start = time.time()
        fallback_result = extract_section_by_section(
            cv_text=cv_text,
            llm_handler=llm_handler,
            model=model,
            existing_sections=result["sections"]
        )
        fallback_time = time.time() - fallback_start

        # Update sections with fallback results
        for section in mandatory_sections:
            if section in fallback_result["sections"] and fallback_result["sections"][section]:
                result["sections"][section] = fallback_result["sections"][section]

        path_steps.append(f"Step 4: Section-by-section fallback completed in {fallback_time:.2f} sec")
        path_steps.append(f"Fallback reasoning: {fallback_result['reasoning']}")

    # Step 5: Add section lengths to path_steps
    section_lengths = {name: len(content) for name, content in result["sections"].items()}
    path_steps.append(f"Section lengths: {', '.join(f'{name}: {length} chars' for name, length in section_lengths.items())}")

    # Step 6: Check validation
    if result["validation"]["is_valid"]:
        path_steps.append(f"Step 5: Validation PASSED - {result['validation']['summary']}")
    else:
        issues = " | ".join(result["validation"]["issues"][:2])
        path_steps.append(f"Step 5: Validation FAILED - {issues}")

    # Step 7: Build final result
    final_result = {}

    # Add all sections (flat structure)
    for section_name, content in result["sections"].items():
        final_result[section_name] = content

    # Add gaps if any
    if "Gaps" in result:
        final_result["Gaps"] = result["Gaps"]

    # Add metadata
    final_result["Section Extraction Time"] = time.time() - start_time
    final_result["Section Extraction Model"] = model

    # Calculate total tokens and cost
    total_prompt_tokens = result["token_usage"]["prompt_tokens"] + result["token_usage"]["completion_tokens"]
    total_cost = result["cost"]["total_cost"]

    if fallback_result:
        total_prompt_tokens += fallback_result.get("token_usage", {}).get("prompt_tokens", 0)
        total_prompt_tokens += fallback_result.get("token_usage", {}).get("completion_tokens", 0)
        total_cost += fallback_result.get("cost", 0)

    final_result["Total Tokens"] = total_prompt_tokens
    final_result["Total Cost"] = total_cost
    final_result["Section Extraction Path"] = "\n".join(path_steps)

    logger.info(f"Section identification completed in {final_result['Section Extraction Time']:.2f}s")
    return final_result
