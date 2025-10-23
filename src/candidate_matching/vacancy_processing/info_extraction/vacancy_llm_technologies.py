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


# Define the overall response structure
class VacancyExtraction(BaseModel):
    """ Represents the full extraction result for a vacancy. """
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
                f"1. **Explicit Technologies**: Directly mentioned in the vacancy.\n"
                f"2. **Implicit Technologies**: \n"
                f"  - Inferred from context, synonyms, or task descriptions. \n"
                f"  - If none are explicitly mentioned, infer them from related technologies.\n"
                f"  - If the vacancy mentions any specific technology, analyze what additional technologies are necessary to work with it. If these technologies are not explicitly mentioned in the vacancy, include them as implicit technologies."
                f"3. **Confidence Score**: "
                f"  - Assign a confidence score (0-100%) for each technology indicates how certain you are that the technology is either explicitly mentioned in the vacancy or can be logically inferred from the context.\n"
                f"  - Be honest. If unsure, assign a lower score.\n"
                "4. **Mandatory vs. Nice-to-Have Technologies**:\n"
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

    max_tokens = max(len(vacancy) * 3, 900)
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


# def parse_llm_vacancy_details_response(response: str, add_tokens_info: bool) -> dict:
#     # Initialize a dictionary to store extracted data
#     extracted_data = {}
#
#     # Split the response into sections
#     sections = response.split('##')
#
#     # Iterate over each section to extract relevant information
#     for section in sections:
#         if ':' in section:
#             # Split section into name and content
#             section_name, section_content = section.split(':', 1)
#             section_name = section_name.strip()
#             section_content = section_content.strip()
#
#             # Extract programming languages if present
#             if section_name == 'Extracted Programming Languages':
#                 lines = [lang.strip('- ').strip() for lang in section_content.split('\n') if lang.strip()]
#                 languages = [lang for lang in lines if not lang.startswith('No ')]
#                 if not languages:
#                     languages = [line for line in lines if line.startswith('No ')]
#                 extracted_data['Extracted Programming Languages'] = ', '.join(languages)
#
#             # Extract technologies if present
#             elif section_name == 'Extracted Technologies':
#                 lines = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
#                 technologies = [tech for tech in lines if not tech.startswith('No ')]
#                 if not technologies:
#                     technologies = [line for line in lines if line.startswith('No ')]
#                 extracted_data['Extracted Technologies'] = ', '.join(technologies)
#
#             # # Extract role if present
#             # elif section_name == 'Extracted Role':
#             #     extracted_data['Extracted Role'] = section_content
#
#             # Extract seniority if present
#             elif section_name == 'Extracted Seniority':
#                 extracted_data['Extracted Seniority'] = section_content
#
#             # Extract industries if present
#             elif section_name == 'Extracted Industries':
#                 extracted_data['Extracted Industries'] = section_content
#
#             # Extract expertise if present
#             elif section_name == 'Extracted Expertise':
#                 extracted_data['Extracted Expertise'] = section_content
#
#             # Extract English level if present
#             elif section_name == 'Extracted English Level':
#                 extracted_data['Extracted English Level'] = section_content
#
#             # Extract reasoning if present
#             elif section_name == 'Reasoning':
#                 extracted_data['Vacancy Reasoning'] = section_content
#
#             # # Extract reasoning about roles if present
#             # elif section_name == 'Reasoning about Roles':
#             #     extracted_data['Reasoning about Roles'] = section_content
#
#             # # Extract matched roles if present
#             # elif section_name == 'Matched Roles':
#             #     lines = [role.strip('- ').strip() for role in section_content.split('\n') if role.strip()]
#             #     matched_roles = [role for role in lines if not role.startswith('No ')]
#             #     if not matched_roles:
#             #         matched_roles = [line for line in lines if line.startswith('No ')]
#             #     extracted_data['Matched Roles'] = ', '.join(matched_roles)
#
#             elif section_name == 'Token Usage and Cost':
#                 token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_details", add_tokens_info=add_tokens_info)
#                 extracted_data.update(token_data)
#
#     return extracted_data
#
#
#
# def extract_vacancy_technologies(vacancy: str, llm_handler: LLMHandler, model, add_tokens_info: bool = False):
#     """
#     Extracts key information from the vacancy description using the language model (LLM).
#     Args:
#     - vacancy (str): The vacancy description.
#     - llm_handler (LLMHandler): Handler for interacting with the language model.
#     Returns:
#     - dict: A dictionary containing the extracted information.
#     """
#     list_of_existing_roles = list(read_specific_columns(['Role Values'], 'values')['Role Values'])
#     existing_roles = ", ".join(list_of_existing_roles)
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": "You are an expert in analyzing job descriptions."
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Your task is to process the provided job description and extract the following information:\n\n"
#                 "1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
#                 f"Explain how you inferred the programming languages, technologies. "
#                 f"If specific libraries or frameworks are mentioned, deduce the programming languages from them.\n"
#                 "2. Extract the key programming languages mentioned in the job description and list them each on a new line. "
#                 f"If no programming languages are explicitly mentioned, infer them from the technologies or libraries listed. "
#                 f"If no programming languages are specified, return 'No programming languages specified'.\n"
#                 "3. Extract the key technologies mentioned in the job description and list them each on a new line. "
#                 f"If a technology has a commonly recognized abbreviation, return the full name followed by the abbreviation in parentheses. "
#                 f"If no technologies are specified, return 'No technologies specified'.\n"
#                 "## Reasoning: The reasoning on how the information was extracted.\n"
#                 "## Extracted Programming Languages: The programming languages extracted by the language model from the vacancy description. Each programming language should be listed on a new line.\n"
#                 "## Extracted Technologies: The technologies extracted by the language model from the vacancy description. Each technology should be listed on a new line.\n"
#                 "\n"
#                 "Here is the input:\n\n"
#                 f"# Job Description:\n"
#                 f"{vacancy}\"\n"
#             )
#         }
#     ]
#
#     # Calculate max tokens based on the length of the vacancy description
#     max_tokens = max(len(vacancy) * 3, 500)
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#
#     response = response.replace("- GitHub\n", "").replace("- Github\n", "").replace("- Git\n", "")
#     response = response.replace("- GitLab\n", "").replace("- Gitlab\n", "")
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_vacancy_details_response(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data
#
#

