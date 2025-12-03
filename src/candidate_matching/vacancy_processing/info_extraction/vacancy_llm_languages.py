from random import randint

from src.data_processing.nlp.languages_info import LanguageItem
from src.data_processing.nlp.llm_handler import LLMHandler


from pydantic import BaseModel, Field
from typing import Literal, Optional, List

RequirementType = Literal[
    "No language requirements",
    "Single language required",
    "All listed languages are required",
    "Any of the listed languages is required"
]

class VacancyLanguagesResponse(BaseModel):
    """Structured response for extracting languages from a job posting."""
    reasoning: str = Field(description="A brief explanation of how languages were extracted from the job posting.")
    requirement_type: RequirementType = Field(description="Type of language requirement.")
    languages: List[LanguageItem] = Field(default_factory=list, description="List of languages and their levels. May be empty if no languages are specified.")


def parse_llm_vacancy_languages(response, add_tokens_info: bool) -> dict:
    extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']
    model = response['model']
    reasoning = f"{extraction.reasoning}\n\n"
    languages_data = extraction.languages
    requirement_type = extraction.requirement_type
    languages_list = [f"{lang.language} {lang.level}" for lang in languages_data]
    languages_list.append(requirement_type)

    if add_tokens_info:
        result = {
            "Extracted Languages": languages_list,
            "Vacancy Languages Reasoning": reasoning,
            "Model Used vacancy_languages": model,
            "Completion Tokens vacancy_languages": str(usage.completion_tokens),
            "Prompt Tokens vacancy_languages": str(usage.prompt_tokens),
            "Cost vacancy_languages": str(cost_info['total_cost'])
        }
    else:
        result = {
            "Extracted Languages": languages_list,
            "Vacancy Languages Reasoning": reasoning,
            "Model Used vacancy_languages": model,
            "Cost vacancy_languages": str(cost_info['total_cost'])
        }
    return result

def extract_vacancy_languages(vacancy: str, llm_handler: 'LLMHandler', model: str, add_tokens_info: bool = False) -> dict:
    """
    Extracts language requirements from the vacancy description using the language model (LLM).

    Args:
        vacancy (str): The vacancy description.
        llm_handler (LLMHandler): Handler for interacting with the language model.
        model (str): Name of the model to use.
        add_tokens_info (bool): Flag to include token usage information.

    Returns:
        dict: A dictionary containing the extracted information.
    """
    cefrlevels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    exml_lvl = randint(0, len(cefrlevels)-2)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in extracting language requirements from job vacancies. "
                "Your task is to carefully review the job description, extract language requirements (if any), "
                "and present them in a structured format."
            )
        },
        {
            "role": "user",
            "content": (
                "Process the job description and extract language requirements:\n\n"
                "1. **Reasoning**: Provide a brief explanation of how you extracted the languages from the text.\n"
                "   - If no languages are found, explain why.\n"
                "   - The language should be explicitly mentioned in the job description.\n"
                "2. **Determine the requirement type**:\n"
                "   - 'No language requirements' if no languages are required.\n"
                "   - 'Single language required' if only one language is required.\n"
                "   - 'All listed languages are required' if all listed languages are required.\n"
                "   - 'Any of the listed languages is required' if any of the listed languages is acceptable.\n"
                "3. **Extract languages and their levels**:\n"
                "   - The language should be explicitly mentioned in the job description.\n"
                "   - Consider 'Fluent' and 'Good' as 'B2'.\n"
                f"   - If a range is provided, such as '{cefrlevels[exml_lvl]}-{cefrlevels[exml_lvl+1]}', "
                f"return the lower edge of the range ('{cefrlevels[exml_lvl]}' in that case).\n"
                "   - If the level is not specified, default to 'B1'.\n"
                "   - If no languages are mentioned, return an empty list.\n"
                "\n"
                f"# Job Description:\n{vacancy}\n"
            )
        }
    ]

    max_tokens = max(len(vacancy), 900)
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=VacancyLanguagesResponse
    )

    extracted_data = parse_llm_vacancy_languages(response, add_tokens_info=add_tokens_info)
    return extracted_data


