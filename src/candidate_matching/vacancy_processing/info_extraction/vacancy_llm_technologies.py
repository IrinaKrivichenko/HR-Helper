import re

from src.data_processing.nlp.llm_handler import LLMHandler

from typing import List, Literal, Optional, Dict, Any, Annotated
from pydantic import BaseModel, Field, validator
from annotated_types import Ge, Le

# Define the structure for a single extracted technology
class ExtractedTechnology(BaseModel):
    """ Represents a single extracted technology from a vacancy. """
    full_name: str = Field(..., description="Full name of the technology.")
    short_name: str = Field(..., description="Shortened name of the technology. If none, repeat the full name.")
    reasoning: str = Field(..., description="Reasoning behind the extraction of this technology.")
    is_programming_language: bool = Field(..., description="Is this a programming language? (True/False)")
    is_mandatory: bool = Field(..., description="Is this technology mandatory? (True/False)")
    mention_type: Literal["explicit", "implicit"] = Field(..., description="Explicit or implicit mention in the vacancy.")
    confidence: Annotated[int, Ge(0), Le(100)]  = Field(..., description="Confidence level (0-100%).", ge=0, le=100)

    @validator('full_name', pre=True, always=True)
    def clean_full_name(cls, value):
        # Remove anything in parentheses and extra spaces
        value = re.sub(r'\([^)]*\)', '', value).strip()
        return value

# Define the overall response structure
class VacancyExtraction(BaseModel):
    """ Represents the full extraction result for a vacancy. """
    main_task_reasoning: str = Field(..., description="Short reasoning about the main task or objective of the vacancy.")
    main_task_technologies_reasoning: str = Field(..., description="Reasoning about the main technologies required for the main task.")
    explicit_tech_reasoning: str = Field(..., description="Reasoning about explicitly mentioned technologies.")
    implicit_tech_reasoning: str = Field(..., description="Reasoning about implicitly mentioned technologies.")
    technologies: List[ExtractedTechnology] = Field(..., description="List of extracted technologies.")

def categorize_technologies(technologies: List[ExtractedTechnology], confidence_threshold: int):
    # Helper function to format technology names
    def format_tech_name(full_name: str, short_name: str) -> str:
        return f"{full_name} ({short_name})" if full_name.find(short_name)<0 else full_name

    # Initialize sets to avoid duplicates
    extracted_programming_languages = set()
    nice_to_have_programming_languages = set()
    extracted_technologies = set()
    nice_to_have_technologies = set()

    # Filter technologies by confidence threshold
    filtered_technologies = [
        tech for tech in technologies
        if tech.confidence >= confidence_threshold
    ]

    # Categorize technologies using sets
    for tech in filtered_technologies:
        formatted_name = format_tech_name(tech.full_name, tech.short_name)
        if tech.is_programming_language:
            if tech.is_mandatory:
                extracted_programming_languages.add(formatted_name)
            else:
                nice_to_have_programming_languages.add(formatted_name)
        else:
            if tech.is_mandatory:
                extracted_technologies.add(formatted_name)
            else:
                nice_to_have_technologies.add(formatted_name)

    # Convert sets back to lists
    result = {
        "Extracted Programming Languages": list(extracted_programming_languages),
        "Nice to have Programming Languages": list(nice_to_have_programming_languages),
        "Extracted Technologies": list(extracted_technologies),
        "Nice to have Technologies": list(nice_to_have_technologies),
    }
    return result


def extract_vacancy_technologies(
    vacancy: str,
    llm_handler: LLMHandler,
    model: str,
    add_tokens_info: bool = False,
    confidence_threshold: int = 65
) -> Dict[str, Any]:
    """
    Extracts technologies from a vacancy text using an LLM.
    Filters technologies by confidence threshold (default: 70%).
    """
    # Define the prompt for the LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical analyst specializing in IT vacancy analysis. "
                "Your task is to extract all technologies mentioned in job vacancies, "
                "including both explicit and implicit references."
            )
        },
        {
            "role": "user",
            "content": (
                "## Task Guidelines:"
                f"1. **Main Task or Objective**: Identify and describe the main task or objective of the vacancy in few sentence.\n"
                f"2. **Main Task Technologies**: Identify and describe the main technologies required to do the main task most effectively. Provide reasoning for each technology.\n"
                f"3. **Explicit Technologies**: Directly mentioned in the vacancy.\n"
                f"4. **Implicit Technologies**: \n"
                f"  - Inferred from context, synonyms, or task descriptions. \n"
                f"  - If none are explicitly mentioned, infer them from related technologies.\n"
                f"  - If the vacancy mentions any specific technology, analyze what additional technologies are necessary to work with it. If these technologies are not explicitly mentioned in the vacancy, include them as implicit technologies."
                f"5. **Confidence Score**: "
                f"  - Assign a confidence score (0-100%) for each technology indicates how certain you are that the technology is either explicitly mentioned in the vacancy or can be logically inferred from the context.\n"
                f"  - Be honest. If unsure, assign a lower score.\n"
                "6. **Mandatory vs. Nice-to-Have Technologies**:\n"
                "  - **Mandatory Technologies**: Use the following criteria to identify mandatory technologies:\n"
                "    - Phrases like 'required', 'must have', 'necessary', 'obligatory', 'essential', 'mandatory', 'need to know'.\n"
                "    - Technologies listed in the main requirements section.\n"
                "    - Technologies mentioned with clear expectations.\n"
                "  - **Nice-to-Have Technologies**: If any of the following keywords are used in relation to a technology, classify it as nice-to-have:\n"
                "    - 'plus', 'advantage', 'desirable', 'is welcome', 'nice to have', 'additional', 'bonus', 'preferred', 'optional', 'beneficial', 'good to have'\n"
                "    - If a technology is mentioned in a 'nice-to-have' or 'additional skills' section.\n"
                f"\n"
                f"**Vacancy:**\n{vacancy}"
            )
        }
    ]

    max_tokens = max(len(vacancy) * 3, 2000)
    # Get the structured response from the LLM
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=VacancyExtraction,
    )

    # Extract the parsed content from the response
    if isinstance(response, dict) and 'parsed' in response:
        extraction = response['parsed']
    else:
        extraction = response


    # Initialize the result dictionary
    result = {
        "Vacancy Technologies Reasoning": (
                f"Main Task Reasoning:\n{extraction.main_task_reasoning}\n\n"
                f"Main Task Technologies Reasoning:\n{extraction.main_task_technologies_reasoning}\n\n"
                f"Explicit Technologies Reasoning:\n{extraction.explicit_tech_reasoning}\n\n"
                f"Implicit Technologies Reasoning:\n{extraction.implicit_tech_reasoning}\n\n"
                f"Individual Technologies Reasoning:\n" +
                "\n".join(
                    f"- {tech.full_name} : {tech.reasoning} (Confidence: {tech.confidence}%, "
                    f"Type: {'Mandatory' if tech.is_mandatory else 'Nice-to-Have'}, "
                    f"Mention: {tech.mention_type})"
                    for tech in extraction.technologies
                )
        ),
        "Model Used vacancy_technologies": model,
        "Cost vacancy_technologies": response["cost"]["total_cost"],
    }
    categorized_lists = categorize_technologies(extraction.technologies, confidence_threshold)
    result.update(categorized_lists)

    # Add token information if required
    if add_tokens_info:
        usage = response["usage"]
        result.update({
            "Completion Tokens": str(usage["completion_tokens"]),
            "Prompt Tokens": str(usage["prompt_tokens"]),
        })

    return result



