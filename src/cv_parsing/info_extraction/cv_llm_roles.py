import json
from typing import List, Literal, Dict, Any, Set, Optional
from pydantic import BaseModel, Field
from src.cv_parsing.info_extraction.new_role_analysis import process_proposed_roles
from src.google_services.sheets import read_specific_columns
from src.nlp.llm_handler import LLMHandler
from src.logger import logger

class RoleMatch(BaseModel):
    name: str = Field(description="Exact role name from predefined list")
    primary_language: Optional[str] = Field(
        default=None,
        description="Primary programming language for this role (if applicable and candidate is proficient)"
    )
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level of the match")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        max_length=9,
        description="Job titles or responsibilities that support this role"
    )

class ProposedRole(BaseModel):
    name: str = Field(description="Proposed new role name")
    primary_language: Optional[str] = Field(
        default=None,
        description="Primary programming language for this role (if applicable and candidate is proficient)"
    )
    justification: str = Field(description="Why this role is needed based on resume analysis")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        max_length=9,
        description="Job titles or responsibilities that fit this role"
    )

class CVRoleExtraction(BaseModel):
    reasoning_steps: List[str] = Field(
        default_factory=list,
        description="Step-by-step analysis in bullet points"
    )
    matched_roles: List[RoleMatch] = Field(
        default_factory=list,
        description="Roles matched from predefined list, with primary language if applicable"
    )
    proposed_roles: List[ProposedRole] = Field(
        default_factory=list,
        description="New roles not in predefined list, with primary language if applicable"
    )

def normalize_role_names(roles: List[str]) -> List[str]:
    """
    Removes duplicate roles and languages in brackets.
    Example:
    ["Data Engineer (Python)", "Data Engineer", "DevOps Engineer (null)"]
    → ["Data Engineer", "DevOps Engineer"]
    """
    normalized = []
    seen = set()
    for role in roles:
        base_role = role.split(" (")[0].strip()
        if base_role not in seen:
            seen.add(base_role)
            normalized.append(base_role)
    return normalized

def extract_cv_roles(
    cv: str,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    """
    Extract and analyze IT roles from a CV.
    Uses programming languages internally for accurate matching but returns only role names.
    """
    # Load existing roles dynamically from Google Sheets
    roles_list: List[str] = list(
        read_specific_columns(['Role Values'], 'values')['Role Values']
    )
    roles_str = ', '.join(f'"{role}"' for role in roles_list)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter and role analyst. "
                "Identify roles AND the primary programming language for each role if the candidate is proficient in it."
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
        response_format=CVRoleExtraction,
    )

    role_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Log the complete LLM response in one entry
    logger.info(f"Field 'Role' LLM response: {role_extraction.model_dump_json(indent=2)}")

    # Validate matched roles against predefined list
    roles_set: Set[str] = set(roles_list)
    validated_matches: List[str] = []  # Теперь это просто список строк
    invalid_matches: List[str] = []

    for match in role_extraction.matched_roles:
        if match.name in roles_set:
            validated_matches.append(match.name)  # Добавляем только имя роли
        else:
            invalid_matches.append(match.name)

    # Combine all proposed roles (original + invalid matches)
    all_proposed_names: List[str] = (
        [prop.name for prop in role_extraction.proposed_roles] +
        invalid_matches
    )

    # Normalize roles before passing to process_proposed_roles
    validated_matches = normalize_role_names(validated_matches)
    all_proposed_unique = normalize_role_names(list(set(all_proposed_names)))

    # Process new roles
    approved_roles, total_new_analysis_cost = process_proposed_roles(
        llm_handler=llm_handler,
        roles_list=roles_list,
        proposed_roles=all_proposed_unique,
        model=model,
    )

    # Combine all roles
    final_roles = validated_matches + approved_roles

    # Build result
    result: Dict[str, Any] = {
            "Role": ', '.join(final_roles),
            "Reasoning about Roles": "\n".join(f"• {step}" for step in role_extraction.reasoning_steps),
            "Model of_Role_CV_extraction": model,
            "Completion Tokens of_Role_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Role_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Role_CV_extraction": cost_info['total_cost'],
            "Cost_of_new_roles_analysis": total_new_analysis_cost,
        }

    logger.info(
        f"CV role extraction completed for field 'Role'. "
        f"Final result: {final_roles}. "
        f"Total cost: ${cost_info['total_cost'] + total_new_analysis_cost:.6f}"
    )

    return result

