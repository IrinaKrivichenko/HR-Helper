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
            "content": (
                "You are a senior technical recruiter with strict criteria for evaluating seniority levels. "
                "Your task is to analyze resumes and assign one of the following seniority levels: "
                "**Principle**, **Senior**, **Middle**, **Junior**, or **Could not determine**. "
                "Follow the decision tree and rules strictly, but interpret the evidence flexibly to avoid 'Could not determine' unless absolutely necessary."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to determine the candidate's seniority level using the strict decision tree and rules.\n\n"
                f"**Decision Tree:**\n"
                f"1. **Principle:** 10+ years relevant IT/Data Science experience AND executive titles (CTO, VP, Director) OR clear evidence of strategic leadership (e.g., shaping company tech strategy, managing multiple teams).\n"
                f"2. **Senior:** 5+ years experience AND at least one of the following:\n"
                f"   - 'Senior' in title OR\n"
                f"   - Project leadership (e.g., leading projects, not just participating) OR\n"
                f"   - Mentoring (e.g., code reviews, training, helping colleagues) OR\n"
                f"   - Architectural responsibilities (e.g., designing systems, choosing tech stacks) OR\n"
                f"   - Independent technical decision-making (e.g., selecting tools, methodologies).\n"
                f"3. **Middle:** 2-5 years experience AND evidence of independent work (e.g., developing features, models, or systems with minimal supervision).\n"
                f"4. **Junior:** Less than 2 years experience OR no evidence of independent work.\n"
                f"5. **Could not determine:** Only if the resume lacks any information about experience, roles, or responsibilities.\n\n"
                f"**Rules:**\n"
                f"- Only count IT/Data Science roles as relevant experience.\n"
                f"- For Principle: Executive titles are preferred, but strategic leadership without a title is acceptable if clearly described.\n"
                f"- For Senior: The presence of any leadership, mentoring, or architectural responsibility is sufficient, even if not explicitly stated.\n"
                f"- For Middle: Independent work is assumed if the candidate has 2+ years of experience and no evidence of junior-level tasks.\n"
                f"- Avoid 'Could not determine' unless the resume is completely unclear or lacks details.\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 800)

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
