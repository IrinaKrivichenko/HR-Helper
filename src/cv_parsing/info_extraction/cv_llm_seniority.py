from pydantic import BaseModel, Field
from typing import List, Literal

from src.nlp.llm_handler import extract_and_parse_token_section, LLMHandler


class CVSeniorityAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    seniority_level: Literal["Junior", "Middle", "Senior", "Principle", "Could not determine"] = Field(
        description="Final seniority classification"
    )


def extract_cv_seniority(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV seniority level using structured outputs.
    """

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
        prompt, model=model, max_tokens=max_tokens,
        response_format=CVSeniorityAnalysis
    )
    # Process structured response
    seniority_analysis = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    result = {}

    if add_tokens_info:
        result["Reasoning about Seniority"] = "\n".join(
            [f"• {step}" for step in seniority_analysis.reasoning_steps])
        result["Model Used"] = model
        result["Completion Tokens"] = str(usage.completion_tokens)
        result["Prompt Tokens"] = str(usage.prompt_tokens)
        cached_tokens = usage.prompt_tokens_details.cached_tokens if hasattr(usage, 'prompt_tokens_details') else 0
        result["Cached Tokens"] = str(cached_tokens)
        result["Cost"] = f"${cost_info['total_cost']:.6f}"

    # Set seniority level
    result["Seniority"] = seniority_analysis.seniority_level
    # Add cost info
    if not add_tokens_info:
        result["Cost_of_Seniority_CV_extraction"] = cost_info['total_cost']
    return result


#
# def _fallback_cv_seniority_parse(response: str, token_data: dict, add_tokens_info: bool) -> dict:
#     result = {}
#
#     if add_tokens_info:
#         result["Reasoning about Seniority"] = "Unable to extract reasoning from response"
#         result.update(token_data)
#
#     # Try to extract seniority from response text
#     seniority_levels = ["Junior", "Middle", "Senior", "Principle", "Could not determine"]
#     found_seniority = "Could not determine"
#
#     for level in seniority_levels:
#         if level in response:
#             found_seniority = level
#             break
#
#     result["Seniority"] = found_seniority
#
#     if "Cost" in token_data and not add_tokens_info:
#         cost = float(token_data["Cost"].replace("$", ""))
#         result["Cost_of_Seniority_CV_extraction"] = cost
#
#     return result
