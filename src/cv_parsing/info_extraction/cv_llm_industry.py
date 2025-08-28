from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
from src.google_services.sheets import read_specific_columns
from src.nlp.llm_handler import LLMHandler

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class IndustryMatch(BaseModel):
    name: str = Field(description="Exact industry name from predefined list")
    confidence: Literal["high", "medium", "low"]
    supporting_projects: List[str] = Field(max_length=5, description="Which projects support this classification")

class ProposedIndustry(BaseModel):
    name: str = Field(description="Proposed new industry name")
    justification: str = Field(description="Why this industry is needed based on projects")
    supporting_projects: List[str] = Field(max_length=3, description="Projects that fit this industry")

class CVIndustryExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    matched_industries: List[IndustryMatch] = Field(default=[], max_length=15)
    proposed_industries: List[ProposedIndustry] = Field(default=[], max_length=8)

def extract_cv_industry(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV industries using SGR approach with dynamic industry list.
    """

    # Load existing industries dynamically from Google Sheets
    industries_list = list(read_specific_columns(['Industry Values'], 'values')['Industry Values'])
    industries_str = '", "'.join(industries_list)
    industries_formatted = f'"{industries_str}"'

    prompt = [
        {
            "role": "system",
            "content": "You are an expert industry analyst specializing in data categorization."
        },
        {
            "role": "user",
            "content": (
                f"Analyze projects in this resume and classify them against existing industries.\n\n"
                f"**Predefined list of accepted industries:** {industries_formatted}\n\n"
                f"**Classification Rules:**\n"
                f"1. Read through all project descriptions to understand their core function and domain\n"
                f"2. For each project, identify potential industries\n"
                f"3. Compare identified industries against the predefined list\n"
                f"4. Match to existing industries when possible\n"
                f"5. Propose new industries only when no good match exists\n"
                f"6. Provide confidence levels and supporting evidence\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = len(cv)

    # Use structured output
    response = llm_handler.get_answer(
        prompt, model=model, max_tokens=max_tokens,
        response_format=CVIndustryExtraction
    )

    # Process structured response
    industry_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Validate matched industries against actual list (важная проверка!)
    industries_set = set(industries_list)
    validated_matches = []
    additional_proposed = []

    for match in industry_extraction.matched_industries:
        if match.name in industries_set:
            validated_matches.append(match.name)
        else:
            # Move invalid matches to proposed (как в оригинале)
            additional_proposed.append(match.name)

    # Combine all proposed industries
    all_proposed_names = ([prop.name for prop in industry_extraction.proposed_industries] +
                          additional_proposed)
    all_proposed_unique = list(set(all_proposed_names))  # Remove duplicates

    # Build initial result
    result = {}

    if add_tokens_info:
        result["Reasoning about Industries"] = "\n".join([f"• {step}" for step in industry_extraction.reasoning_steps])
        result["Model Used"] = model
        result["Completion Tokens"] = str(usage.completion_tokens)
        result["Prompt Tokens"] = str(usage.prompt_tokens)
        result["Cost"] = f"${cost_info['total_cost']:.6f}"

    # Process new industries individually (как вы хотели!)
    approved_industries, total_new_analysis_cost = process_proposed_industries(
        llm_handler=llm_handler,
        existing_industries_list=industries_list,
        proposed_industries=all_proposed_unique,
        model=model
    )

    # Final result
    final_industries = list(set(validated_matches + approved_industries))
    result["Industry"] = ', '.join(final_industries)

    if not add_tokens_info:
        result["Cost_of_industry_CV_extraction"] = cost_info['total_cost']
        result["Cost_of_new_industries_analysis"] = total_new_analysis_cost

    return result

