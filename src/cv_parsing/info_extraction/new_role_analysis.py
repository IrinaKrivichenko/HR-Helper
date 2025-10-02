import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Tuple, Dict

from src.google_services.sheets import write_specific_columns
from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler

class RoleAnalysis(BaseModel):
    proposed_role: str = Field(description="Name of the proposed role being analyzed")
    pros: List[str] = Field(max_length=5, description="Arguments for adding this role")
    cons: List[str] = Field(max_length=5, description="Arguments against adding this role")
    justification: str = Field(description="Final reasoning for the decision")
    recommendation: Literal["Add", "Overlaps"] = Field(description="Final recommendation")
    overlaps_with: Optional[str] = Field(default=None, description="Existing role it overlaps with (if recommendation is Overlaps)")


def process_proposed_roles(
        llm_handler: LLMHandler,
        roles_list: List[str],
        proposed_roles: List[str],
        model: str = "gpt-4.1-mini",
        service=None  # Google Sheets service
) -> Tuple[List[str], float]:
    """
    Process proposed roles using SGR approach.
    Each role is analyzed separately for maximum reliability.
    """

    if len(proposed_roles) == 0:
        return [], 0.0

    print("!!!!!!! proposed_roles:", str(proposed_roles))

    to_add = []
    overlaps = []
    total_cost = 0.0

    for proposed in proposed_roles:
        # Analyze single role with structured output
        analysis_result, cost = _analyze_single_role(
            proposed, roles_list, llm_handler, model
        )

        total_cost += cost

        if analysis_result["recommendation"] == "Add":
            to_add.append(proposed)
        elif analysis_result["recommendation"] == "Overlaps" and analysis_result["overlaps_with"]:
            overlap_roles = analysis_result["overlaps_with"]
            if isinstance(overlap_roles, str):
                overlap_roles = [overlap_roles]
            for overlap_role in overlap_roles:
                if overlap_role in roles_list:
                    overlaps.append(overlap_role)
            else:
                logger.error(f"Overlap role '{overlap_role}' not found in master list")

    # Update Google Sheets with new roles (как в оригинале!)
    if to_add and service:
        updated_roles = sorted(list(set(roles_list + to_add)))
        updated_df = pd.DataFrame({"Role Values": updated_roles})
        rows_to_highlight = [i for i, role in enumerate(updated_roles) if role in to_add]
        # write_specific_columns(df=updated_df, sheet_name="values", service=service, rows_to_highlight=rows_to_highlight)

    to_add = [f"NEW {role}" for role in to_add]
    # Return combined list and total cost
    combined_list = to_add + overlaps
    return combined_list, total_cost


def _analyze_single_role(proposed_role: str,
                         existing_roles: List[str],
                         llm_handler: LLMHandler,
                         model: str) -> Tuple[Dict, float]:
    """
    Analyze a single proposed role using SGR.
    """

    roles_str = f'"{", ".join(existing_roles)}"'

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter and role analyst. "
                "Your task is to analyze a single proposed role for inclusion in a master list of IT roles. "
                "Your analysis must be precise and follow strict non-overlapping principles."
            )
        },
        {
            "role": "user",
            "content": (
                f"Current master list of roles: {roles_str}\n\n"
                f"The master list must adhere to two principles:\n"
                f"1. **Non-Overlapping**: Each role must represent a unique function\n"
                f"2. **Comprehensive**: The list must cover most IT roles\n\n"
                f"Analyze the following proposed role: **{proposed_role}**\n\n"
                f"Provide thorough analysis with pros, cons, and final recommendation."
            )
        }
    ]

    # Use structured output
    response = llm_handler.get_answer(
        prompt, model=model, max_tokens=1000,
        response_format=RoleAnalysis
    )

    # Process response
    analysis = response['parsed']
    cost = response['cost']['total_cost']

    # Convert to dictionary format
    result = {
        "proposed_role": analysis.proposed_role,
        "pros": analysis.pros,
        "cons": analysis.cons,
        "justification": analysis.justification,
        "recommendation": analysis.recommendation,
        "overlaps_with": analysis.overlaps_with,
        "cost": cost
    }

    return result, cost

