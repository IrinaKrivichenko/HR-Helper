from collections import Counter

from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler

from random import choice
from typing import List, Optional, Literal, Type, Dict, Any
from pydantic import BaseModel, Field, create_model
from annotated_types import MinLen, MaxLen
from typing_extensions import Annotated

def create_vacancy_role_extraction_model(roles_list: List[str]) -> Type[BaseModel]:
    """
    Creates a Pydantic model for vacancy role extraction.
    """
    if not roles_list:
        raise ValueError("Roles list cannot be empty")

    # Define a Literal type for allowed roles
    # roles_list.append("No Role is specified")
    RoleType = Literal[*roles_list]

    class VacancyRoleMatch(BaseModel):
        """ Model for a single role matched from the vacancy."""
        reasoning_about_matching: Annotated[List[str], MaxLen(5)] = Field(default_factory=list, description="Reasoning why this role matches the vacancy")
        name: RoleType = Field(description="Final role name from the predefined list")
        is_consistent: bool =  Field(description="Whether the selected role matches the reasoning_about_matching"),
        corrected_role : Optional[RoleType] = Field(default=None, description="Corrected role if is_consistent=False or repeat the same role if the choice was correct."),
        match_percentage: int = Field(ge=0, le=100, description="Percentage of how well the role matches the vacancy (0-100)"
                                                " - 80-100%: The role is a direct specialization or synonym."
                                                " - 60-79%: The role is semantically close"
                                                " - 0%: The role is unrelated."
                                      )

    class VacancyExtraction(BaseModel):
        """ Main model for vacancy extraction."""
        who_is_needed_reasoning: str = Field(..., description="Short reasoning about who is actually needed for this vacancy.")
        reasoning: str = Field(description="General reasoning about the vacancy analysis. Please be brief.")
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
        reasoning_about_roles: str = Field(description="Reasoning about which roles from the predefined list match the vacancy. Please be brief.")
        matched_roles: Annotated[List[VacancyRoleMatch], MinLen(5), MaxLen(7)] = Field(
            default_factory=list,
            description="List of nearest matched roles from the predefined list (at least one)"
        )

    return VacancyExtraction


def create_few_shot_example() -> Dict[str, Any]:
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

    # Create a user example
    few_shot_example = {
        "role": "user",
        "content": (
            f"Analyze the following vacancy and extract the required information:\n\n"
            f"**Vacancy:**\n"
            f"An American company is seeking an experienced {example_role} for a group of projects, "
            f"representing various AI solutions (projects in various fields, from Computer Vision to NLP). "
            f"With knowledge of PyTorch, TensorFlow, and pandas libraries."
        )
    }

    # Create an assistant response example
    few_shot_response = {
        "role": "assistant",
        "content": (
            f"""{{
                "reasoning": "The job description mentions the need for an 'experienced' {example_role}, 
which indicates a 'Senior' level. The libraries PyTorch, TensorFlow, and Pandas suggest the use of the Python programming language. 
The role in the vacancy is '{example_role}'.",
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
                "reasoning_about_roles": "The role of '{example_role}' requires a strong background in machine learning, 
as evidenced by the need for experience with libraries such as PyTorch, TensorFlow, and Pandas. 
The role involves working on projects related to Computer Vision (CV) and Natural Language Processing (NLP).",
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


def filter_roles(
    matched_roles: List[Any],  # Теперь matched_roles — это список объектов VacancyRoleMatch
    match_threshold: int = 0
) -> List[str]:
    """
    Filters roles by match percentage and returns the names of the most suitable roles.
    Logic:
    1. Uses corrected_role if is_consistent=False.
    2. Returns all role names with match_percentage >= match_threshold.
    3. If no roles meet the threshold, returns all role names with the highest match_percentage.
    4. If all match_percentage are 0, returns repeated role names.
    5. If none of the above, returns ["No Role is specified"].
    """
    # Step 1: Replace role names with corrected_role if is_consistent=False
    corrected_roles = []
    for role in matched_roles:
        final_role = role.corrected_role if not role.is_consistent and role.corrected_role else role.name
        corrected_roles.append({
            'name': final_role,
            'match_percentage': role.match_percentage
        })

    # Step 2: Filter role names by threshold
    filtered_role_names = [
        role['name']
        for role in corrected_roles
        if role['match_percentage'] >= match_threshold
    ]

    # If roles remain after filtering, return their names
    if filtered_role_names:
        return filtered_role_names

    # Step 3: If no roles above threshold, find role names with the highest match_percentage
    max_percentage = max(role['match_percentage']  for role in corrected_roles)  # Используем role.match_percentage

    if max_percentage > 0:
        # Return names of all roles with the maximum percentage
        return [
            role['name']
            for role in corrected_roles
            if role['match_percentage'] == max_percentage
        ]
    else:
        # Step 4: All match_percentage are 0, find repeated role names
        role_names = [role['name'] for role in corrected_roles]
        name_counts = Counter(role_names)
        repeated_role_names = [
            role['name']
            for role in corrected_roles
            if name_counts[role['name']] > 1
        ]
        if repeated_role_names:
            # Remove duplicates while preserving order
            seen = set()
            unique_repeated_role_names = []
            for name in repeated_role_names:
                if name not in seen:
                    seen.add(name)
                    unique_repeated_role_names.append(name)
            return unique_repeated_role_names
        else:
            # Step 5: If nothing matches, return ["No Role is specified"]
            return ["No Role is specified"]


def extract_vacancy_role(
    vacancy: str,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano",
    add_tokens_info: bool = False,
    match_threshold: int = 55
) -> Dict[str, Any]:
    model = "gpt-4.1-mini"
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
        read_specific_columns(['Role Values'], 'values')['Role Values']
    )
    roles_str = ', '.join(f'"{role}"' for role in roles_list)
    few_shot_example, few_shot_response = create_few_shot_example()

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
                f"3. Identify the role directly from the vacancy.\n"
                f"4. Identify the seniority level described in the job description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
                f"A 'Senior' should be a specialist with at least three years of experience. "
                f"Only 'Senior' can be a Lead or develop system-level architecture. "
                f"Consider adjectives like 'крутой', 'cool', or 'strong' as indicators of higher seniority 'Senior'. "
                f"If no seniority level is explicitly mentioned, infer it from the context. "
                f"If multiple seniority levels are mentioned, return the **highest** level.\n"
                f"If no seniority level is explicitly mentioned and cannot be inferred from context (e.g., years of experience, responsibilities), return 'Any'.\n"
                f"5. Match the extracted role with the predefined roles and provide a match percentage (0-100) for each.\n"
                f"Important note: The predefined roles list includes **both technical and non-technical roles**. "
                f"6. Provide reasoning for each step.\n\n"
            )
        },
        # {
        #     "role": "user",
        #     "content": "Example starts here:"
        # },
        # few_shot_example,
        # few_shot_response,
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
    max_tokens = max(len(vacancy) * 9, 4012)

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
    filtered_roles = filter_roles(role_extraction.matched_roles, match_threshold)

    # Prepare the result dictionary
    result = {
        "Extracted Role": role_extraction.extracted_role,
        # "Extracted Programming Languages": role_extraction.extracted_programming_languages,
        # "Extracted Technologies": role_extraction.extracted_technologies,
        "Extracted Seniority": role_extraction.seniority,
        "Matched Roles": filtered_roles,
        "Vacancy Roles Reasoning": (
            f"Main Task Reasoning:\n{role_extraction.who_is_needed_reasoning}\n\n"
            f"{role_extraction.reasoning}\n\n"
            f"{role_extraction.reasoning_about_roles}\n\n"
            + "\n\n".join(
                [
                    f"Role: {role.name}\n"
                    f"Reasoning: {'; '.join(role.reasoning_about_matching)}\n"
                    f"Consistent: {role.is_consistent}\n"
                    f"Corrected role name: {role.corrected_role}\n"
                    f"Match Percentage: {role.match_percentage}"
                    for role in role_extraction.matched_roles
                ]
            ) +
            f"\n\nmatch_threshold = {match_threshold}"
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



