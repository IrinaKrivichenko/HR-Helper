import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Literal, Dict, Any, Set, Optional, Type, Union
from pydantic import BaseModel, Field, create_model
from annotated_types import MinLen
from typing_extensions import Annotated
from src.cv_parsing.info_extraction.new_role_analysis import process_proposed_roles, process_roles_list
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.allowed_values_matcher import match_values
from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger



def create_role_match_model(roles_list: List[str]) -> Type[BaseModel]:
    """
    Dynamically creates RoleMatch model with Literal type based on roles_list.
    Args:
        roles_list: List of allowed roles for Literal type.
    Returns:
        Pydantic model RoleMatch with Literal type for 'name' field.
    """
    if not roles_list:
        raise ValueError("Roles list cannot be empty")
    RoleType = Literal[*roles_list]  # For Python < 3.11: Literal.__getitem__(tuple(roles_list))
    return create_model(
        'RoleMatch',
        supporting_evidence=(List[str], Field(default_factory=list, max_length=9, description="Job titles or responsibilities that support this role (provide evidence first)")),
        primary_language=(Optional[str], Field(default=None, description="Primary programming language IF role involves coding. Leave empty for non-technical roles.")),
        name=(RoleType, Field(description="Final decision: exact role name from predefined list based on above analysis")),
        confidence=(Literal["high", "medium", "low"], Field(description="Confidence based on evidence strength: high=direct match, medium=inferred, low=partial")),
        )

class ProposedRole(BaseModel):
    """Model for proposed new roles not in the predefined list."""
    supporting_evidence: List[str] = Field(default_factory=list, max_length=9, description="Job titles or responsibilities that fit this role (provide evidence first)")
    primary_language: Optional[str] = Field(default=None, description="Primary programming language IF role involves coding. Leave empty for non-technical roles.")
    justification: str = Field(description="Why this role is needed based on resume analysis (explain reasoning)")
    name: str = Field(description="Final decision: proposed new role name based on above analysis")

def create_cv_role_extraction_model(roles_list: List[str]) -> Type[BaseModel]:
    """
    Creates CVRoleExtraction model with dynamic RoleMatch and static ProposedRole.
    Args:
        roles_list: List of allowed roles for RoleMatch.
    Returns:
        Pydantic model CVRoleExtraction.
    """
    # Create dynamic RoleMatch model
    RoleMatch = create_role_match_model(roles_list)
    # Use static ProposedRole model
    ProposedRole_model = ProposedRole
    # Create CVRoleExtraction model
    CVRoleExtraction = create_model(
        'CVRoleExtraction',
        reasoning_steps=(List[str], Field(default_factory=list, description="Step-by-step analysis in bullet points")),
        matched_roles=(Annotated[List[RoleMatch], MinLen(5)], Field(default_factory=list, description="Roles matched from predefined list, with primary language if applicable")),
        proposed_roles=(List[ProposedRole_model], Field(default_factory=list, description="New roles not in predefined list, with primary language if applicable")),
    )
    return CVRoleExtraction

def extract_main_roles(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    roles_list: List[str],
    model: str
) -> Dict[str, Any]:
    """
    Extracts up to 3 main roles from the entire resume.
    """
    cv_text = get_section_for_field(cv_sections, "Role")
    roles_str = ', '.join(f'"{role}"' for role in roles_list)
    print(roles_str)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter. "
                "Identify **up to 3 main roles** the candidate has performed across the entire resume. "
                "Focus on the most prominent roles based on responsibilities and projects. "
                "Use only the predefined list of roles."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to identify up to 3 main roles.\n\n"
                f"**Predefined list of roles:** {roles_str}\n\n"
                f"**Classification Rules:**\n"
                f"1. Scan job titles and project responsibilities\n"
                f"2. Ignore seniority (e.g., Senior/Junior/Middle)\n"
                f"3. Match to existing roles when possible\n"
                f"4. Propose new roles only when no good match exists\n\n"
                f"**Resume:**\n{cv_text}"
            )
        }
    ]

    CVRoleExtraction = create_cv_role_extraction_model(roles_list)
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=3022,
        response_format=CVRoleExtraction,
    )
    return response

def extract_additional_roles_for_project(
    project_text: str,
    llm_handler: LLMHandler,
    roles_list: List[str],
    model: str
) -> Dict[str, Any]:
    """
    Extracts all roles performed in a single project.
    """
    roles_str = ', '.join(f'"{role}"' for role in roles_list)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter. "
                "Identify **all roles** the candidate performed in this project. "
                "Use only the predefined list of roles."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this project to identify all roles.\n\n"
                f"**Predefined list of roles:** {roles_str}\n\n"
                f"**Classification Rules:**\n"
                f"1. Scan job titles and project responsibilities\n"
                f"2. Ignore seniority (e.g., Senior/Junior/Middle)\n"
                f"3. Match to existing roles when possible\n"
                f"4. Propose new roles only when no good match exists\n\n"
                f"**Project:**\n{project_text}"
            )
        }
    ]

    CVRoleExtraction = create_cv_role_extraction_model(roles_list)
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        response_format=CVRoleExtraction,
    )
    return response

def extract_cv_roles(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    """
    Extract and analyze IT roles from a CV, separating main and additional roles.
    Main roles are extracted from the entire resume, additional roles are extracted per project.
    """
    start_time = time.time()
    roles_list: List[str] = list(
        read_specific_columns(['Role Values'], 'values')['Role Values']
    )

    # Extract projects from the resume
    projects_list = get_section_for_field(cv_sections, "Projects")

    # Parallel extraction of main roles and additional roles
    with ThreadPoolExecutor() as executor:
        main_roles_future = executor.submit(
            extract_main_roles,
            cv_sections,
            llm_handler,
            roles_list,
            model
        )
        additional_roles_futures = [
            executor.submit(
                extract_additional_roles_for_project,
                project_text,
                llm_handler,
                roles_list,
                model
            )
            for project_text in projects_list
        ]

        main_roles_response = main_roles_future.result()
        additional_roles_responses = [future.result() for future in as_completed(additional_roles_futures)]

    # Extract parsed data
    main_roles_data = main_roles_response['parsed']
    additional_roles_data = [response['parsed'] for response in additional_roles_responses]

    # Combine usage and cost
    total_usage = {
        'completion_tokens': main_roles_response['usage'].completion_tokens +
                           sum(response['usage'].completion_tokens for response in additional_roles_responses),
        'prompt_tokens': main_roles_response['usage'].prompt_tokens +
                        sum(response['usage'].prompt_tokens for response in additional_roles_responses)
    }
    total_cost = main_roles_response['cost']['total_cost'] + \
                 sum(response['cost']['total_cost'] for response in additional_roles_responses)

    # Extract all role names
    main_roles_names = []
    for role in main_roles_data.matched_roles:
        if role.confidence == "high":
            main_roles_names.append(role.name)
    for proposed_role in main_roles_data.proposed_roles:
        main_roles_names.append(f"NEW {proposed_role.name}")

    additional_roles_names = []
    for response in additional_roles_responses:
        parsed_data = response['parsed']
        for role in parsed_data.matched_roles:
            if role.confidence == "high":
                if role.name not in main_roles_names and role.name not in additional_roles_names:
                    additional_roles_names.append(role.name)
        for proposed_role in parsed_data.proposed_roles:
            new_role_name = f"NEW {proposed_role.name}"
            if new_role_name not in main_roles_names  and new_role_name not in additional_roles_names:
                additional_roles_names.append(new_role_name)

    # Build detailed reasoning
    reasoning_about_roles = []

    # Add main roles reasoning
    reasoning_about_roles.append("MAIN ROLES:")
    for role in main_roles_data.matched_roles:
        reasoning_about_roles.append(
            f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
            f"Primary language: {role.primary_language or 'N/A'}\n"
            f"Role name: {role.name}\n"
            f"Confidence: {role.confidence}"
        )
    # Add proposed main roles reasoning
    if main_roles_data.proposed_roles:
        reasoning_about_roles.append("\nPROPOSED MAIN ROLES:")
        for role in main_roles_data.proposed_roles:
            reasoning_about_roles.append(
                f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
                f"Primary language: {role.primary_language or 'N/A'}\n"
                f"Justification: {role.justification}\n"
                f"Proposed role: NEW {role.name}"
            )

    # Add additional roles reasoning
    reasoning_about_roles.append("\n\nADDITIONAL ROLES:")
    for response in additional_roles_responses:
        parsed_data = response['parsed']
        for role in parsed_data.matched_roles:
            reasoning_about_roles.append(
                f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
                f"Primary language: {role.primary_language or 'N/A'}\n"
                f"Role name: {role.name}\n"
                f"Confidence: {role.confidence}"
            )

    # Add proposed additional roles reasoning
    proposed_additional_roles = [
        role for response in additional_roles_responses
        for role in response['parsed'].proposed_roles
    ]
    if proposed_additional_roles:
        reasoning_about_roles.append("\nPROPOSED ADDITIONAL ROLES:")
        for role in proposed_additional_roles:
            reasoning_about_roles.append(
                f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
                f"Primary language: {role.primary_language or 'N/A'}\n"
                f"Justification: {role.justification}\n"
                f"Proposed role: NEW {role.name}"
            )

    # Build result
    result: Dict[str, Any] = {
        "Main Roles": ", ".join(main_roles_names),
        "Additional Roles": ', '.join(additional_roles_names),
        "Reasoning about Roles": "\n".join(reasoning_about_roles),
        "Model of_Role_CV_extraction": model,
        "Completion Tokens of_Role_CV_extraction": str(total_usage['completion_tokens']),
        "Prompt Tokens of_Role_CV_extraction": str(total_usage['prompt_tokens']),
        "Cost_of_Role_CV_extraction": total_cost,
        "Cost_of_new_roles_analysis": 0,
        "Time": time.time() - start_time,
    }

    logger.info(
        f"CV role extraction completed. "
        f"Main Roles: {main_roles_names}. "
        f"Additional Roles: {additional_roles_names}. "
        f"Total cost: ${total_cost + 0:.6f}"
    )

    return result

