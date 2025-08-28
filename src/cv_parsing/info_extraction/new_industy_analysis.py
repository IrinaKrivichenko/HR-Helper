import pandas as pd
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Tuple, Dict

from src.google_services.sheets import write_specific_columns
from src.logger import logger
from src.nlp.llm_handler import LLMHandler


class IndustryAnalysis(BaseModel):
    proposed_industry: str = Field(description="Name of the proposed industry being analyzed")
    pros: List[str] = Field(max_length=5, description="Arguments for adding this industry")
    cons: List[str] = Field(max_length=5, description="Arguments against adding this industry")
    justification: str = Field(description="Final reasoning for the decision")
    recommendation: Literal["Add", "Overlaps"] = Field(description="Final recommendation")
    overlaps_with: Optional[str] = Field(default=None, description="Existing industry it overlaps with (if recommendation is Overlaps)")


def process_proposed_industries(
        llm_handler: LLMHandler,
        existing_industries_list: List[str],
        proposed_industries: List[str],
        model: str = "gpt-4.1-nano",
        service=None  # Google Sheets service
) -> Tuple[List[str], float]:
    """
    Process proposed industries using SGR approach.
    Each industry is analyzed separately for maximum reliability.
    """

    if len(proposed_industries) == 0:
        return [], 0.0

    print("!!!!!!! proposed_industries:", str(proposed_industries))

    # Format existing industries for prompt
    industries_str = f'"{", ".join(existing_industries_list)}"'

    to_add = []
    overlaps = []
    total_cost = 0.0

    for proposed in proposed_industries:
        # Analyze single industry with structured output
        analysis_result, cost = _analyze_single_industry(
            proposed, existing_industries_list, llm_handler, model
        )

        total_cost += cost

        if analysis_result["recommendation"] == "Add":
            to_add.append(proposed)
        elif analysis_result["recommendation"] == "Overlaps" and analysis_result["overlaps_with"]:
            overlap_industry = analysis_result["overlaps_with"]
            if isinstance(overlap_industry, str):
                if overlap_industry in existing_industries_list:
                    overlaps.append(overlap_industry)
                else:
                    logger.error(f"Overlap industry '{overlap_industry}' not found in master list")

    # Update Google Sheets with new industries (как в оригинале!)
    if to_add:
        updated_industries = sorted(list(set(existing_industries_list + to_add)))
        updated_df = pd.DataFrame({"Industry Values": updated_industries})
        rows_to_highlight = [i for i, industry in enumerate(updated_industries) if industry in to_add]
        write_specific_columns(df=updated_df, sheet_name="values", service=service, rows_to_highlight=rows_to_highlight)

    # Return combined list and total cost
    combined_list = to_add + overlaps
    return combined_list, total_cost


def _analyze_single_industry(proposed_industry: str,
                             existing_industries: List[str],
                             llm_handler: LLMHandler,
                             model: str) -> Tuple[Dict, float]:
    """
    Analyze a single proposed industry using SGR.
    """

    industries_str = f'"{", ".join(existing_industries)}"'

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a senior data architect and taxonomist. "
                "Your task is to analyze a single proposed industry for inclusion in a master list of IT project industries. "
                "Your analysis must be precise, logical, and follow strict non-overlapping principles."
            )
        },
        {
            "role": "user",
            "content": (
                f"Current master list of industries: {industries_str}\n\n"
                f"The master list must adhere to two principles:\n"
                f"1. **Non-Overlapping**: Each industry must represent a unique domain\n"
                f"2. **Comprehensive**: The list must cover most IT project domains\n\n"
                f"Analyze the following proposed industry: **{proposed_industry}**\n\n"
                f"Provide thorough analysis with pros, cons, and final recommendation."
            )
        }
    ]

    # Use structured output
    response = llm_handler.get_answer(
        prompt, model=model, max_tokens=1000,
        response_format=IndustryAnalysis
    )

    # Process response
    analysis = response['parsed']
    cost = response['cost']['total_cost']

    # Convert to dictionary format
    result = {
        "proposed_industry": analysis.proposed_industry,
        "pros": analysis.pros,
        "cons": analysis.cons,
        "justification": analysis.justification,
        "recommendation": analysis.recommendation,
        "overlaps_with": analysis.overlaps_with,
        "cost": cost
    }

    return result, cost

