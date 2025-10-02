import json
import time

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class CVNameExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    first_name: Optional[str] = Field(default=None, description="First name of the candidate")
    last_name: Optional[str] = Field(default=None, description="Last name of the candidate")
    full_name_found: Optional[str] = Field(default=None, description="Full name as found in resume (if available)")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level of name extraction")

    @validator("first_name", "last_name", "full_name_found", pre=True, always=True)
    def capitalize_names(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        return " ".join(
            word.capitalize() for word in v.split()
        )


def extract_cv_name(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
):
    """
    Extract candidate name from a resume using Schema-Guided Reasoning (SGR) approach.
    Names are automatically capitalized. If last name is missing, returns "Hidden".
    """
    start_time = time.time()
    cv = get_section_for_field(cv_sections, "Name")
    prompt = [
        {
            "role": "system",
            "content": "You are an expert HR analyst specializing in resume parsing and name extraction."
        },
        {
            "role": "user",
            "content": (
                f"Extract the candidate's name from this resume.\n\n"
                f"**Extraction Rules:**\n"
                f"1. Look for name in header, contact section, or signature\n"
                f"2. Distinguish between first name and last name\n"
                f"3. Ignore company names, project names, or references\n"
                f"4. If name is unclear or missing, set confidence to 'low'\n"
                f"5. Provide reasoning for your extraction\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 100)  # Names don't need many tokens

    # Use structured output
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=CVNameExtraction
    )

    # Process structured response
    name_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Build result dictionary with all fields
    result = {
        "First Name": name_extraction.first_name or "",
        "Last Name": name_extraction.last_name or "Hidden",
        "Reasoning about Name": "\n".join(f"• {step}" for step in name_extraction.reasoning_steps),
        "Name Confidence": name_extraction.confidence,
        "Full Name Found": name_extraction.full_name_found or "",
        "Model of_Name_CV_extraction": model,
        "Completion Tokens of_Name_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens _of_Name_CV_extraction": str(usage.prompt_tokens),
        "Cost_of_Name_CV_extraction": cost_info['total_cost'],
            "Time" : time.time()-start_time,
    }

    # Log the complete response in a single entry
    logger.info(
        f"Field extraction completed - Fields: 'First Name', 'Last Name' | Response: {json.dumps(result, ensure_ascii=False)}")

    return result
