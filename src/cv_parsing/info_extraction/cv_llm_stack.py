import json
import time

from pydantic import BaseModel, Field
from typing import List, Dict

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class TechnologyItem(BaseModel):
    name: str = Field(description="Technology name in format 'Full Name (Abbreviation)' if applicable")
    score: int = Field(ge=1, le=5, description="Proficiency score from 1-5")


class CVStackAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    technologies: List[TechnologyItem] = Field(description="List of identified technologies with scores")


def extract_cv_stack(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
):
    """
    Extract CV technology stack - now with structured outputs by default.
    """
    start_time = time.time()
    cv = get_section_for_field(cv_sections, "Stack")
    prompt = [
        {
            "role": "system",
            "content": "You are an expert technical analyst specializing in IT resume analysis."
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to extract technology skills with proficiency scores.\n\n"
                f"**Scoring Criteria:**\n"
                f"- **5 - Expert:** 3+ projects OR Advanced certification + 2+ projects\n"
                f"- **4 - Proficient:** 2 projects OR Skills section + 1 project\n"
                f"- **3 - Competent:** Intermediate certification OR Skills section only\n"
                f"- **2 - Foundational:** 1 project OR Foundational certification\n"
                f"- **1 - Mentioned:** Peripheral mention only\n\n"
                f"Use format 'Full Name (Abbreviation)' where applicable.\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 200)

    # Get structured response from LLM
    structured_response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=CVStackAnalysis
    )

    # Process structured response
    cv_analysis = structured_response['parsed']
    usage = structured_response['usage']
    cost_info = structured_response['cost']

    # Format stack string
    stack_string = ""
    if cv_analysis.technologies:
        sorted_techs = sorted(cv_analysis.technologies, key=lambda x: x.score, reverse=True)
        stack_string = ", ".join([f"{tech.name} - {tech.score}" for tech in sorted_techs])

    # Get cached tokens if available
    cached_tokens = 0
    if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    # Build result dictionary with all fields
    result = {
        "Stack": stack_string,
        "Reasoning about Stack": "\n".join(f"• {step}" for step in cv_analysis.reasoning_steps),
        "Model of_Stack_CV_extraction": model,
        "Completion Tokens of_Stack_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens _of_Stack_CV_extraction": str(usage.prompt_tokens),
        "Cached Tokens of_Stack_CV_extraction": str(cached_tokens),
        "Cost_of_Stack_CV_extraction": cost_info['total_cost'],
            "Time" : time.time()-start_time,
    }

    # Log the complete response in a single entry
    logger.info(f"Field extraction completed - Field: 'Stack' | Response: {json.dumps(result, ensure_ascii=False)}")

    return result
