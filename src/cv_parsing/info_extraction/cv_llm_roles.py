
from src.cv_parsing.info_extraction.new_role_analysis import process_proposed_roles
from src.google_services.sheets import read_specific_columns
from src.nlp.llm_handler import  LLMHandler

from pydantic import BaseModel, Field
from typing import List, Literal

class RoleMatch(BaseModel):
    name: str = Field(description="Exact role name from predefined list")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence level of the match")
    supporting_evidence: List[str] = Field(max_length=5, description="Job titles or responsibilities that support this role")

class ProposedRole(BaseModel):
    name: str = Field(description="Proposed new role name")
    justification: str = Field(description="Why this role is needed based on resume analysis")
    supporting_evidence: List[str] = Field(max_length=3, description="Job titles or responsibilities that fit this role")

class CVRoleExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    matched_roles: List[RoleMatch] = Field(default=[], max_length=20, description="Roles matched from predefined list")
    proposed_roles: List[ProposedRole] = Field(default=[], max_length=10, description="New roles not in predefined list")


def extract_cv_roles(cv: str, llm_handler: LLMHandler, model="gpt-4.1-mini", add_tokens_info: bool = False):
    """
    Extract CV roles using SGR approach with dynamic role list.
    """

    # Load existing roles dynamically from Google Sheets
    roles_list = list(read_specific_columns(['Role Values'], 'values')['Role Values'])
    roles_str = '", "'.join(roles_list)
    roles_formatted = f'"{roles_str}"'

    prompt = [
        {
            "role": "system",
            "content": "You are an expert technical recruiter and role analyst."
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to identify all IT roles the candidate has performed.\n\n"
                f"**Predefined list of accepted roles:** {roles_formatted}\n\n"
                f"**Classification Rules:**\n"
                f"1. Scan job titles and project responsibilities\n"
                f"2. **Ignore Seniority** - focus on core function (ignore Senior/Junior/Middle)\n"
                f"3. **Be Specific with Developers** - map to specific programming language (e.g., 'Python Developer')\n"
                f"4. **Map Responsibilities to Roles** - analyze tasks to identify roles even if not explicitly named\n"
                f"5. Match to existing roles when possible\n"
                f"6. Propose new roles only when no good match exists\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 200)

    # Use structured output
    response = llm_handler.get_answer(
        prompt, model=model, max_tokens=max_tokens,
        response_format=CVRoleExtraction
    )

    # Process structured response
    role_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Validate matched roles against actual list (важная проверка!)
    roles_set = set(roles_list)
    validated_matches = []
    additional_proposed = []

    for match in role_extraction.matched_roles:
        if match.name in roles_set:
            validated_matches.append(match.name)
        else:
            # Move invalid matches to proposed (как в оригинале)
            additional_proposed.append(match.name)

    # Combine all proposed roles
    all_proposed_names = ([prop.name for prop in role_extraction.proposed_roles] +
                          additional_proposed)
    all_proposed_unique = list(set(all_proposed_names))  # Remove duplicates

    # Build initial result
    result = {}

    if add_tokens_info:
        result["Reasoning about Roles"] = "\n".join([f"• {step}" for step in role_extraction.reasoning_steps])
        result["Model Used cv_roles"] = model
        result["Completion Tokens cv_roles"] = str(usage.completion_tokens)
        result["Prompt Tokens cv_roles"] = str(usage.prompt_tokens)
        result["Cost cv_roles"] = f"${cost_info['total_cost']:.6f}"

    # Process new roles individually (как вы хотели!)
    approved_roles, total_new_analysis_cost = process_proposed_roles(
        llm_handler=llm_handler,
        roles_list=roles_list,
        proposed_roles=all_proposed_unique,
        model=model
    )

    # Final result
    final_roles = list(set(validated_matches + approved_roles))
    result["Role"] = ', '.join(final_roles)

    if not add_tokens_info:
        result["Cost_of_Role_CV_extraction"] = cost_info['total_cost']
        result["Cost_of_new_roles_analysis"] = total_new_analysis_cost

    return result


