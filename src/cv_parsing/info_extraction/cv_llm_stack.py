from pydantic import BaseModel, Field
from typing import List

from src.nlp.llm_handler import extract_and_parse_token_section, LLMHandler

class TechnologyItem(BaseModel):
    name: str = Field(description="Technology name in format 'Full Name (Abbreviation)' if applicable")
    score: int = Field(ge=1, le=5, description="Proficiency score from 1-5")

class CVStackAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    technologies: List[TechnologyItem] = Field(description="List of identified technologies with scores")


def extract_cv_stack(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV technology stack - now with structured outputs by default.
    """
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
    # Try structured output first
    structured_response = llm_handler.get_answer(
            prompt, model=model, max_tokens=max_tokens,
            response_format=CVStackAnalysis
        )
    # Process structured response
    cv_analysis = structured_response['parsed']
    usage = structured_response['usage']
    cost_info = structured_response['cost']

    result = {}

    if add_tokens_info:
        result["Reasoning about Stack"] = "\n".join([f"• {step}" for step in cv_analysis.reasoning_steps])
        result["Model Used"] = model
        result["Completion Tokens"] = str(usage.completion_tokens)
        result["Prompt Tokens"] = str(usage.prompt_tokens)
        cached_tokens = usage.prompt_tokens_details.cached_tokens if hasattr(usage, 'prompt_tokens_details') else 0
        result["Cached Tokens"] = str(cached_tokens)
        result["Cost"] = f"${cost_info['total_cost']:.6f}"

    # Format stack string
    if cv_analysis.technologies:
        sorted_techs = sorted(cv_analysis.technologies, key=lambda x: x.score, reverse=True)
        stack_string = ", ".join([f"{tech.name} - {tech.score}" for tech in sorted_techs])
        result["Stack"] = stack_string
    else:
        result["Stack"] = ""

    if not add_tokens_info:
        result["Cost_of_Stack_CV_extraction"] = cost_info['total_cost']

    return result

