import json
import re
import time

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class TechnologyItem(BaseModel):
    """Represents a single technology from a CV with its proficiency score."""
    reasoning_about_technology: str = Field(default="", description="One sentence reasoning about the technology proficiency")
    full_name: str = Field(..., description="Full name of the technology.")
    short_name: str = Field(..., description="Shortened name of the technology. If none, repeat the full name.")
    score: int = Field(ge=1, le=5, description="Proficiency score from 1-5"
                f"**Scoring Criteria:**\n"
                f"- **5 - Expert:** 3+ projects OR Advanced certification + 2+ projects\n"
                f"- **4 - Proficient:** 2 projects OR Skills section + 1 project\n"
                f"- **3 - Competent:** Intermediate certification OR Skills section only\n"
                f"- **2 - Foundational:** 1 project OR Foundational certification\n"
                f"- **1 - Mentioned:** Peripheral mention only\n"
                       )

    @field_validator('full_name', mode='before')
    def clean_full_name(cls, value):
        # Remove anything in parentheses and extra spaces
        value = re.sub(r'\([^)]*\)', '', value).strip()
        return value

class CVStackAnalysis(BaseModel):
    """Represents the full analysis result for a CV."""
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    technologies: List[TechnologyItem] = Field(description="List of identified technologies with scores")


def extract_cv_stack(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1"
):
    """Extract CV technology stack - now with structured outputs by default."""
    start_time = time.time()
    cv = get_section_for_field(cv_sections, "Stack")
    prompt = [
        {
            "role": "system",
            "content":(
                "You are an expert technical analyst specializing in IT resume analysis. "
                "**Your task is to extract ALL technologies mentioned in the resume, even if they are only mentioned once.** "
                "Do not miss any technology."
            )
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
                f"Make sure you include all the technologies from this CV in your answer.\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv)*9, 3000)

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
    # Use a dictionary to merge duplicate technologies and keep the highest score
    tech_dict: Dict[str, TechnologyItem] = {}
    for tech in cv_analysis.technologies:
        key = tech.short_name # f"{tech.full_name} ({tech.short_name})" if tech.full_name != tech.short_name else tech.full_name
        if key in tech_dict:
            # Keep the technology with the highest score
            if tech.score > tech_dict[key].score:
                tech_dict[key] = tech
        else:
            tech_dict[key] = tech
    # Convert the dictionary values back to a list
    unique_technologies = list(tech_dict.values())
    # Sort technologies by score
    sorted_techs = sorted(unique_technologies, key=lambda x: x.score, reverse=True)
    # Format stack string
    sorted_techs_str = [f"{tech.full_name} ({tech.short_name}) - {tech.score}"
                if tech.full_name != tech.short_name else
                    f"{tech.full_name} - {tech.score}"
                        for tech in sorted_techs ]
    stack_string = ", ".join(sorted_techs_str)

    # Format reasoning about stack: each technology with its reasoning
    reasoning_about_stack = ""
    if cv_analysis.technologies:
        reasoning_about_stack = "\n".join(
            [f"• {tech.full_name} ({tech.short_name}): {tech.reasoning_about_technology}" for tech in sorted_techs]
        )

    # Get cached tokens if available
    cached_tokens = 0
    if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    # Build result dictionary with all fields
    result = {
        "Stack": stack_string,
        "Reasoning about Stack": reasoning_about_stack,
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
