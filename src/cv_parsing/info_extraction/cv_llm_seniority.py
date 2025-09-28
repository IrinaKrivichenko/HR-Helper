import json
import time

from pydantic import BaseModel, Field
from typing import List, Literal, Dict

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class CVSeniorityAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    seniority_level: Literal["Junior", "Middle", "Senior", "Principle", "Could not determine"] = Field(
        description="Final seniority classification"
    )


def extract_cv_seniority(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
):
    """
    Extract CV seniority level using structured outputs.
    """
    start_time = time.time()
    cv = get_section_for_field(cv_sections, "Seniority")
    prompt = [
        {
            "role": "system",
            "content": "You are a senior technical recruiter with strict criteria for evaluating seniority levels."
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to determine the candidate's seniority level using the strict decision tree.\n\n"
                f"**Decision Tree:**\n"
                f"1. **Principle:** 10+ years relevant IT/Data Science experience AND executive titles (CTO, VP, Director)\n"
                f"2. **Senior:** 5+ years experience AND 'Senior' title AND mentoring/architectural responsibilities\n"
                f"3. **Middle:** 2-5 years experience AND independent work with minimal supervision\n"
                f"4. **Junior:** Default if none above are met\n\n"
                f"**Rules:**\n"
                f"- Only count IT/Data Science roles as relevant experience\n"
                f"- Executive titles required for Principle (project leadership ≠ executive)\n"
                f"- If insufficient evidence, use 'Could not determine'\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = len(cv)

    # Use structured output with existing get_answer method
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=CVSeniorityAnalysis
    )

    # Process structured response
    seniority_analysis = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Get cached tokens if available
    cached_tokens = 0
    if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    # Build result dictionary with all fields
    result = {
        "Seniority": seniority_analysis.seniority_level,
        "Reasoning about Seniority": "\n".join(f"• {step}" for step in seniority_analysis.reasoning_steps),
        "Model of_Seniority_CV_extraction": model,
        "Completion Tokens of_Seniority_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens _of_Seniority_CV_extraction": str(usage.prompt_tokens),
        "Cached Tokens of_Seniority_CV_extraction": str(cached_tokens),
        "Cost_of_Seniority_CV_extraction": cost_info['total_cost'],
            "Time" : time.time()-start_time,
    }

    # Log the complete response in a single entry
    logger.info(f"Field extraction completed - Field: 'Seniority' | Response: {json.dumps(result, ensure_ascii=False)}")

    return result
