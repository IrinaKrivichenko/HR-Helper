from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler

from random import choice
from typing import List, Optional, Literal, Type, Dict, Any
from pydantic import BaseModel, Field, create_model
from annotated_types import MinLen
from typing_extensions import Annotated

def create_vacancy_role_extraction_model(roles_list: List[str]) -> Type[BaseModel]:
    """
    Creates a Pydantic model for vacancy role extraction.
    """
    if not roles_list:
        raise ValueError("Roles list cannot be empty")

    # Define a Literal type for allowed roles
    roles_list.append("No Role is specified")
    RoleType = Literal[*roles_list]

    class VacancyRoleMatch(BaseModel):
        """ Model for a single role matched from the vacancy."""
        reasoning_about_matching: List[str] = Field(default_factory=list, max_items=9, description="Reasoning why this role matches the vacancy")
        name: RoleType = Field(description="Final role name from the predefined list")
        match_percentage: int = Field(ge=0, le=100, description="Percentage of how well the role matches the vacancy (0-100)")

    class VacancyExtraction(BaseModel):
        """ Main model for vacancy extraction."""
        main_task_reasoning: str = Field(..., description="Short reasoning about the main task or objective of the vacancy.")
        reasoning: str = Field(description="General reasoning about the vacancy analysis")
        extracted_programming_languages: List[str] = Field(default_factory=list, description="List of programming languages mentioned in the vacancy")
        extracted_technologies: List[str] = Field(default_factory=list, description="List of technologies mentioned in the vacancy")
        extracted_role: str = Field(description="Role extracted directly from the vacancy")
        seniority: Literal["Any", "Junior", "Middle", "Senior", "Principal"] = Field(
            description=(
                "Seniority level described in the job description. "
                "If no seniority level is explicitly mentioned, infer it from the context. "
                "If unsure, return 'Any'."
            )
        )
        reasoning_about_roles: str = Field(description="Reasoning about which roles from the predefined list match the vacancy")
        matched_roles: Annotated[List[VacancyRoleMatch], MinLen(7)] = Field(
            default_factory=list,
            description="List of nearest matched roles from the predefined list (at least one)"
        )

    return VacancyExtraction


def create_few_shot_example(roles_list: List[str]) -> Dict[str, Any]:
    """
    Creates a few-shot example for the prompt.
    Args:
        roles_list: List of predefined roles.
    Returns:
        Dict[str, Any]: Dictionary with user and assistant examples.
    """
    # Randomly select a role for the example
    all_possible_roles = ["Machine Learning Engineer", "Data Scientist", "AI Engineer"]
    example_role = choice(all_possible_roles)
    other_roles = [role for role in all_possible_roles if role != example_role]
    roles_str = ', '.join(f'"{role}"' for role in roles_list)

    # Create a user example
    few_shot_example = {
        "role": "user",
        "content": (
            f"Analyze the following vacancy and extract the required information:\n\n"
            f"**Predefined roles:** {roles_str}\n\n"
            f"**Vacancy:**\n"
            f"Американская компания в поиске опытного {example_role} на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas. Уровень английского: C1. Зарплата - до 8000-10000$ gross."
        )
    }

    # Create an assistant response example
    few_shot_response = {
        "role": "assistant",
        "content": (
            f"""{{
                "reasoning": "The job description mentions the need for an 'опытного' (experienced) {example_role}, which indicates a 'Senior' level. The libraries PyTorch, TensorFlow, and Pandas suggest the use of the Python programming language. The role in the vacancy is '{example_role}'.",
                "extracted_programming_languages": ["Python"],
                "extracted_technologies": [
                    "Machine Learning (ML)",
                    "Computer Vision (CV)",
                    "Natural Language Processing (NLP)",
                    "PyTorch",
                    "TensorFlow",
                    "Pandas"
                ],
                "extracted_role": "{example_role}",
                "seniority": "Senior",
                "reasoning_about_roles": "The role of '{example_role}' requires a strong background in machine learning, as evidenced by the need for experience with libraries such as PyTorch, TensorFlow, and Pandas. The role involves working on projects related to Computer Vision (CV) and Natural Language Processing (NLP).",
                "matched_roles": [
                    {{
                        "reasoning_about_matching": [
                            "The vacancy explicitly states the role as '{example_role}', which corresponds to '{example_role}' in the predefined list.",
                            "The required skills with PyTorch, TensorFlow, and pandas are typical for a {example_role}.",
                            "The projects involve AI solutions in Computer Vision and NLP, which are common domains for {example_role}."
                        ],
                        "name": "{example_role}",
                        "match_percentage": 100
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves AI solutions and machine learning libraries, which also relate to the '{other_roles[0]}' role.",
                            "The vacancy mentions AI projects in Computer Vision and NLP, which are relevant to {other_roles[0]}."
                        ],
                        "name": "{other_roles[0]}",
                        "match_percentage": 85
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves AI solutions and machine learning libraries, which also relate to the '{other_roles[1]}' role.",
                            "The vacancy mentions AI projects in Computer Vision and NLP, which are relevant to {other_roles[1]}."
                        ],
                        "name": "{other_roles[1]}",
                        "match_percentage": 85
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves working with deep learning libraries like PyTorch and TensorFlow, which are relevant for 'Deep Learning Engineer'.",
                            "The projects include Computer Vision and NLP, common areas for Deep Learning Engineers."
                        ],
                        "name": "Deep Learning Engineer",
                        "match_percentage": 80
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves working on NLP projects, which is relevant for 'NLP Engineer'.",
                            "The vacancy mentions NLP as one of the project domains."
                        ],
                        "name": "NLP Engineer",
                        "match_percentage": 75
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves working on Computer Vision projects, which is relevant for 'Computer Vision Engineer'.",
                            "The vacancy mentions Computer Vision as one of the project domains."
                        ],
                        "name": "Computer Vision Engineer",
                        "match_percentage": 75
                    }},
                    {{
                        "reasoning_about_matching": [
                            "The role involves working with machine learning models and research, which is relevant for 'Machine Learning Researcher'.",
                            "The vacancy mentions AI projects and machine learning libraries."
                        ],
                        "name": "Machine Learning Researcher",
                        "match_percentage": 70
                    }}
                ]
            }}"""
        )
    }

    return few_shot_example, few_shot_response

def extract_vacancy_role(
    vacancy: str,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-mini",
    add_tokens_info: bool = False,
    match_threshold: int = 55
) -> Dict[str, Any]:
    """
    Extracts roles, programming languages, and technologies from a vacancy description.
    Returns a structured dictionary with the extracted information.

    Args:
        vacancy (str): The vacancy description.
        llm_handler (LLMHandler): Handler for interacting with the language model.
        model (str): The model to use for extraction.
        add_tokens_info (bool): If True, adds token usage information to the output.

    Returns:
        Dict[str, Any]: A dictionary containing the extracted information.
    """
    # Load predefined roles
    roles_list: List[str] = list(
        read_specific_columns(['Role Values'], 'values', remove_emonji=True)['Role Values']
    )
    roles_str = ', '.join(f'"{role}"' for role in roles_list)
    few_shot_example, few_shot_response = create_few_shot_example(roles_list)

    # Create the dynamic Pydantic model
    VacancyExtraction = create_vacancy_role_extraction_model(roles_list)

    # Define the prompt for the LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in analyzing job vacancies. "
                "Extract programming languages, and technologies, the role and seniority from the vacancy. "
                "Match the extracted role with the predefined list of roles. "
                "Provide detailed reasoning for each step."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze the following vacancy and extract the required information:\n\n"
                f"**Predefined roles:** {roles_str}\n\n"
                f"**Rules:**\n"                
                f"1. Identify and describe the main task or objective of the vacancy in few sentence.\n"
                f"2. Extract all programming languages and technologies mentioned.\n"
                f"3. Identify the role directly from the vacancy. If no role is specified, return 'No Role is specified'.\n"
                f"4. Identify the seniority level described in the job description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
                f"A 'Senior' should be a specialist with at least three years of experience. "
                f"Only 'Senior' can be a Lead or develop system-level architecture. "
                f"Consider adjectives like 'крутой', 'cool', or 'strong' as indicators of higher seniority 'Senior'. "
                f"If no seniority level is explicitly mentioned, infer it from the context. "
                f"If multiple seniority levels are mentioned, return the **highest** level.\n"
                f"If no seniority level is explicitly mentioned and cannot be inferred from context (e.g., years of experience, responsibilities), return 'Any'.\n"
                f"5. Match the extracted role with the predefined roles and provide a match percentage (0-100) for each.\n"
                f"6. Provide reasoning for each step.\n\n"
            )
        },
        {
            "role": "user",
            "content": "Example starts here:"
        },
        few_shot_example,
        few_shot_response,
        {
            "role": "user",
            "content": "Example ends here. Now analyze the following vacancy:"
        },
        {
            "role": "user",
            "content": (
                f"**Predefined roles:** {roles_str}\n\n"
                f"**Vacancy:**\n{vacancy}"
            )
        }
    ]

    # Calculate max tokens
    max_tokens = max(len(vacancy) * 4, 900)

    # Get the structured response from the LLM
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=VacancyExtraction,
    )

    # Parse the response
    role_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Filtering roles by threshold
    filtered_roles = [
        role for role in role_extraction.matched_roles
        if role.match_percentage >= match_threshold
    ]
    # If there are no roles left after filtering, take the role with the highest match_percentage
    if not filtered_roles:
        max_role = max(role_extraction.matched_roles, key=lambda x: x.match_percentage)
        filtered_roles = [max_role]

    # Prepare the result dictionary
    result = {
        "Extracted Role": role_extraction.extracted_role,
        # "Extracted Programming Languages": role_extraction.extracted_programming_languages,
        # "Extracted Technologies": role_extraction.extracted_technologies,
        "Extracted Seniority": role_extraction.seniority,
        "Matched Roles": [role.name for role in filtered_roles],
        "Vacancy Roles Reasoning": (
            f"Main Task Reasoning:\n{role_extraction.main_task_reasoning}\n\n"
            f"{role_extraction.reasoning}\n\n"
            f"{role_extraction.reasoning_about_roles}\n\n"
            + "\n\n".join(
                [
                    f"Role: {role.name}\n"
                    f"Reasoning: {'; '.join(role.reasoning_about_matching)}\n"
                    f"Match Percentage: {role.match_percentage}"
                    for role in role_extraction.matched_roles
                ]
            )
        ),
        "Model Used vacancy_roles": model,
        "Cost vacancy_roles": cost_info['total_cost'],
    }

    # Add token information if required
    if add_tokens_info:
        result.update({
            "Completion Tokens": str(usage.completion_tokens),
            "Prompt Tokens": str(usage.prompt_tokens),
        })

    return result






#
#
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
#                 extracted_data['Extracted Programming Languages'] = '\n'.join(languages)
#
#             # Extract technologies if present
#             elif section_name == 'Extracted Technologies':
#                 lines = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
#                 technologies = [tech for tech in lines if not tech.startswith('No ')]
#                 if not technologies:
#                     technologies = [line for line in lines if line.startswith('No ')]
#                 extracted_data['Extracted Technologies'] = '\n'.join(technologies)
#
#             # Extract role if present
#             elif section_name == 'Extracted Role':
#                 extracted_data['Extracted Role'] = section_content
#
#             # Extract reasoning if present
#             elif section_name == 'Reasoning':
#                 extracted_data['Vacancy Reasoning'] = section_content
#
#             # Extract reasoning about roles if present
#             elif section_name == 'Reasoning about Roles':
#                 extracted_data['Reasoning about Roles'] = section_content
#
#             # Extract matched roles if present
#             elif section_name == 'Matched Roles':
#                 lines = [role.strip('- ').strip() for role in section_content.split('\n') if role.strip()]
#                 matched_roles = [role for role in lines if not role.startswith('No ')]
#                 if not matched_roles:
#                     matched_roles = [line for line in lines if line.startswith('No ')]
#                 extracted_data['Matched Roles'] = '\n'.join(matched_roles)
#
#             elif section_name == 'Token Usage and Cost':
#                 token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_details", add_tokens_info=add_tokens_info)
#                 extracted_data.update(token_data)
#
#     return extracted_data
#
#
#
# def extract_vacancy_role(vacancy: str, llm_handler: LLMHandler, model, add_tokens_info: bool = False):
#     """
#     Extracts key information from the vacancy description using the language model (LLM).
#     Args:
#     - vacancy (str): The vacancy description.
#     - llm_handler (LLMHandler): Handler for interacting with the language model.
#     Returns:
#     - dict: A dictionary containing the extracted information.
#     """
#     example_role = choice(["ML Engineer", "Data Scientist", "ML Scientist"])
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
#                 "Your task is to process the provided job description and extract the information about role:\n\n"
#                 "1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
#                 f"Explain how you inferred the programming languages, technologies, seniority level, role, English level, industries, expertise. "
#                 f"If specific libraries or frameworks are mentioned, deduce the programming languages from them.\n"
#                 "2. Extract the key programming languages mentioned in the job description and list them each on a new line. "
#                 f"If no programming languages are explicitly mentioned, infer them from the technologies or libraries listed. "
#                 f"If no programming languages are specified, return 'No programming languages are specified'.\n"
#                 "3. Extract the key technologies mentioned in the job description and list them each on a new line. "
#                 f"If a technology has a commonly recognized abbreviation, return the full name followed by the abbreviation in parentheses. "
#                 f"If no technologies are specified, return 'No technologies are specified'.\n"
#                 "4. Identify the role described in the job description. The role should not include seniority. "
#                 f"Extract the role directly from the job description. If no role is specified, return 'No role is specified'.\n"
#                 "5. Identify the seniority level described in the job description. "
#                 f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
#                 f"A 'Senior' should be a specialist with at least three years of experience. "
#                 f"Only 'Senior' can be a Lead or develop system-level architecture. "
#                 f"Consider adjectives like 'крутой', 'cool', or 'strong' as indicators of higher seniority 'Senior'."
#                 f"If no seniority level is explicitly mentioned, infer it from the context. If unsure, return 'Any'.\n"
#                 "6.  Reasoning about Roles: Provide reasoning on which roles from the list of existing roles could be suitable for this job description. "
#                 f"Compare the extracted role with the following list of existing roles: {existing_roles}. "
#                 f"Explain why certain roles match based on the overlap in required skills and technologies.\n"
#                 "7. Matched Roles: List all approximately matching roles from the existing roles list, each on a new line with a dash. If there are no matches at all, write 'NEW' followed by the role extracted from the vacancy.\n"
#                 f"The output should be formatted in Markdown with the following sections:\n"
#                 "## Reasoning: The reasoning on how the information was extracted.\n"
#                 "## Extracted Programming Languages: The programming languages extracted by the language model from the vacancy description. Each programming language should be listed on a new line.\n"
#                 "## Extracted Technologies: The technologies extracted by the language model from the vacancy description. Each technology should be listed on a new line.\n"
#                 "## Extracted Role: The role corresponding to the vacancy description extracted directly from the job description.\n"
#                 "## Reasoning about Roles: The reasoning on which roles from the list of existing roles could be suitable for this job description.\n"
#                 "## Matched Roles: The roles from the existing roles list that match the extracted role, each on a new line with a dash. If no matches are found, write 'NEW' followed by the role extracted from the vacancy.\n"
#                 f"\n"
#                 "Here is an example:\n\n"
#                 "# Example Input:\n"
#                 f"Американская компания в поиске опытного {example_role} на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas. Уровень английского: C1. Зарплата - до 8000-10000$ gross.\n"
#                 f"\n"
#                 "# Example Output:\n"
#                 f"## Reasoning: The job description mentions the need for an 'опытного' (experienced) {example_role}, which indicates a 'Senior' level. The libraries PyTorch,TensorFlow, and Pandas suggest the use of the Python programming language. The role in the vacancy is '{example_role}'. The salary mentioned is up to 8000-10000$ gross, which is interpreted as 8000-10000$ per month. The English level mentioned is C1. No industry or expertise is mentioned.\n"
#                 "## Extracted Programming Languages:\n"
#                 f"  - Python\n"
#                 "## Extracted Technologies:\n"
#                 f"  - Machine Learning (ML)\n"
#                 f"  - Computer Vision (CV)\n"
#                 f"  - Natural Language Processing (NLP)\n"
#                 f"  - PyTorch\n"
#                 f"  - TensorFlow\n"
#                 f"  - Pandas\n"
#                 f"## Extracted Role: {example_role}\n"
#                 "## Extracted Seniority: Senior\n"
#                 f"## Reasoning about Roles: The role of \"{example_role}\" requires a strong background in machine learning, as evidenced by the need for experience with libraries such as PyTorch, TensorFlow, and Pandas, which are commonly used in machine learning and data analysis tasks, supports this match. Additionally, the role involves working on projects related to Computer Vision (CV) and Natural Language Processing (NLP). AI Engineer: This role is a good match because AI Engineers often work on similar technologies and projects involving machine learning and artificial intelligence. They typically have experience with the same libraries and frameworks mentioned in the job description. Data Scientist: Data Scientists also work extensively with machine learning models and data analysis, making this role a suitable match. They often use similar tools and techniques to extract insights and build predictive models. DL Engineer: Deep Learning Engineers specialize in developing and implementing deep learning models, which aligns well with the requirements of this job description. Their expertise in deep learning frameworks like PyTorch and TensorFlow is particularly relevant. ML Researcher: ML Researchers focus on advancing the field of machine learning through research and development. Their deep understanding of machine learning algorithms and techniques makes them a good fit for this role. CV Engineer: Given the mention of Computer Vision in the job description, a CV Engineer, who specializes in this area, is a relevant match. NLP Engineer: Similarly, the mention of Natural Language Processing tasks makes an NLP Engineer a suitable match for this role.\n"
#                 "## Matched Roles:\n"
#                 f"  - AI Engineer\n"
#                 f"  - Computer Vision Engineer\n"
#                 f"  - Data Scientist\n"
#                 f"  - Deep Learning Engineer\n"
#                 f"  - Machine Learning Engineer\n"
#                 f"  - NLP Engineer\n"
#                 f"  - Machine Learning Researcher\n"
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

