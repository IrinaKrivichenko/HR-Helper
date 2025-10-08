import time
from typing import List, Literal, Dict, Any, Set, Optional, Type, Union
from pydantic import BaseModel, Field, create_model
from src.cv_parsing.info_extraction.new_role_analysis import process_proposed_roles
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
        supporting_evidence=(List[str], Field(
            default_factory=list,
            max_length=9,
            description="Job titles or responsibilities that support this role (provide evidence first)"
        )),
        primary_language=(Optional[str], Field(
            default=None,
            description="Primary programming language IF role involves coding. Leave empty for non-technical roles."
        )),
        confidence=(Literal["high", "medium", "low"], Field(
            description="Confidence based on evidence strength: high=direct match, medium=inferred, low=partial"
        )),
        name=(RoleType, Field(
            description="Final decision: exact role name from predefined list based on above analysis"
        )),
    )

class ProposedRole(BaseModel):
    """Model for proposed new roles not in the predefined list."""
    supporting_evidence: List[str] = Field(
        default_factory=list,
        max_length=9,
        description="Job titles or responsibilities that fit this role (provide evidence first)"
    )
    primary_language: Optional[str] = Field(
        default=None,
        description="Primary programming language IF role involves coding. Leave empty for non-technical roles."
    )
    justification: str = Field(
        description="Why this role is needed based on resume analysis (explain reasoning)"
    )
    name: str = Field(
        description="Final decision: proposed new role name based on above analysis"
    )

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
        reasoning_steps=(List[str], Field(
            default_factory=list,
            description="Step-by-step analysis in bullet points"
        )),
        matched_roles=(List[RoleMatch], Field(
            default_factory=list,
            description="Roles matched from predefined list, with primary language if applicable"
        )),
        proposed_roles=(List[ProposedRole_model], Field(
            default_factory=list,
            description="New roles not in predefined list, with primary language if applicable"
        )),
    )
    return CVRoleExtraction


def extract_cv_roles(
        cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    """
    Extract and analyze IT roles from a CV.
    Uses programming languages internally for accurate matching but returns only role names.
    """
    start_time = time.time()
    # Load existing roles dynamically from Google Sheets
    roles_list: List[str] = list(
        read_specific_columns(['Role Values'], 'values', remove_emonji=True)['Role Values']
    )
    roles_str = ', '.join(f'"{role}"' for role in roles_list)

    cv = get_section_for_field(cv_sections, "Role")
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter and role analyst. "
                "Identify the primary programming languages AND roles for each role if the candidate is proficient in it."
                "Analyze the resume step-by-step, focusing on projects and responsibilities."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to identify all IT roles the candidate has performed, "
                f"including the primary programming language for each role if the candidate is proficient in it.\n\n"
                f"**Predefined list of accepted roles:** {roles_str}\n\n"
                f"**Classification Rules:**\n"
                f"1. Scan job titles and project responsibilities\n"
                f"2. **Ignore Seniority** - focus on core function (ignore Senior/Junior/Middle)\n"
                f"3. **Be Specific with Developers** - map to specific programming language (e.g., 'Python Developer')\n"
                f"4. **Map Responsibilities to Roles** - analyze tasks to identify roles even if not explicitly named\n"
                f"5. **Identify Primary Language** - for each role, specify the primary programming language if the candidate is proficient in it (e.g., 'Python', 'JavaScript', 'Java')\n"
                f"6. Match to existing roles when possible\n"
                f"7. Propose new roles only when no good match exists\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = min(max(len(cv), 200), 4096)

    # Get structured response from LLM
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=create_cv_role_extraction_model(roles_list),
    )

    role_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Log the complete LLM response in one entry
    logger.info(f"Field 'Role' LLM response: {role_extraction.model_dump_json(indent=2)}")

    # Extract role names
    all_roles_returned_from_llm = [
        role.name for role in role_extraction.matched_roles + role_extraction.proposed_roles
    ]
    # Match roles to predefined list
    matches_roles_set, proposed_roles_set = match_values(roles_list, all_roles_returned_from_llm)
    # Process new roles
    approved_roles, total_new_analysis_cost = process_proposed_roles(
        llm_handler=llm_handler,
        roles_list=roles_list,
        proposed_roles=list(proposed_roles_set),
        model=model,
    )
    # Combine all roles
    final_roles = list(matches_roles_set.union(approved_roles))

    # Extract role names and build detailed reasoning
    reasoning_about_roles = []
    # Add reasoning steps from CVRoleExtraction
    reasoning_about_roles.extend(role_extraction.reasoning_steps)
    # Add supporting evidence from matched roles
    for role in role_extraction.matched_roles:
        reasoning_about_roles.append(
            f"Matched role: {role.name} (confidence: {role.confidence})\n"
            f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
            f"Primary language: {role.primary_language or 'N/A'}"
        )
    # Add supporting evidence from proposed roles
    for role in role_extraction.proposed_roles:
        reasoning_about_roles.append(
            f"Proposed role: {role.name}\n"
            f"Supporting evidence: {', '.join(role.supporting_evidence)}\n"
            f"Justification: {role.justification}\n"
            f"Primary language: {role.primary_language or 'N/A'}"
        )

    # Build result
    result: Dict[str, Any] = {
            "Role": ', '.join(final_roles),
            "Reasoning about Roles": "\n".join(reasoning_about_roles),
            "Model of_Role_CV_extraction": model,
            "Completion Tokens of_Role_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Role_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Role_CV_extraction": cost_info['total_cost'],
            "Cost_of_new_roles_analysis": total_new_analysis_cost,
            "Time" : time.time()-start_time,
        }
    logger.info(
        f"CV role extraction completed for field 'Role'. "
        f"Final result: {final_roles}. "
        f"Total cost: ${cost_info['total_cost'] + total_new_analysis_cost:.6f}"
    )
    return result

