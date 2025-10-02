import json
import time
from typing import List, Literal, Dict
from pydantic import BaseModel, Field
from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class IndustryMatch(BaseModel):
    name: str = Field(description="Exact industry name from predefined list")
    confidence: Literal["high", "medium", "low"]
    supporting_projects: List[str] = Field(max_length=5, description="Which projects support this classification")


class ProposedIndustry(BaseModel):
    name: str = Field(description="Proposed new industry name")
    justification: str = Field(description="Why this industry is needed based on projects")
    supporting_projects: List[str] = Field(max_length=3, description="Projects that fit this industry")


class CVIndustriesExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    matched_industries: List[IndustryMatch] = Field(default=[], max_length=15)
    proposed_industries: List[ProposedIndustry] = Field(default=[], max_length=8)


def extract_cv_industries(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
):
    """
    Extract CV industries using SGR approach with dynamic industries list.
    """
    start_time = time.time()
    # Load existing industries dynamically from Google Sheets
    industries_list = list(read_specific_columns(['Industries Values'], 'values', remove_emonji=True)['Industries Values'])
    industries_str = '", "'.join(industries_list)
    industries_formatted = f'"{industries_str}"'

    cv = get_section_for_field(cv_sections, "Industries")
    prompt = [
        {
            "role": "system",
            "content": "You are an expert industries analyst specializing in data categorization."
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

    max_tokens = max(len(cv), 200)

    # Use structured output
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=CVIndustriesExtraction
    )

    # Process structured response
    industries_extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Validate matched industries against actual list (important validation!)
    industries_set = set(industries_list)
    validated_matches = []
    additional_proposed = []

    for match in industries_extraction.matched_industries:
        if match.name in industries_set:
            validated_matches.append(match.name)
        else:
            # Move invalid matches to proposed (as in original)
            additional_proposed.append(match.name)

    # Combine all proposed industries
    all_proposed_names = ([prop.name for prop in industries_extraction.proposed_industries] +
                          additional_proposed)
    all_proposed_unique = list(set(all_proposed_names))  # Remove duplicates

    # Process new industries individually
    approved_industries, total_new_analysis_cost = process_proposed_industries(
        llm_handler=llm_handler,
        existing_industries_list=industries_list,
        proposed_industries=all_proposed_unique,
        model=model
    )

    # Final result
    final_industries = list(set(validated_matches + approved_industries))

    # Build result dictionary with all fields
    result = {
        "Industries": ', '.join(final_industries),
        "Reasoning about Industries": "\n".join(f"• {step}" for step in industries_extraction.reasoning_steps),
        "Model of_Industries_CV_extraction": model,
        "Completion Tokens of_Industries_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens of_Industries_CV_extraction": str(usage.prompt_tokens),
        "Cost_of_industries_CV_extraction": cost_info['total_cost'],
        "Cost_of_new_industries_analysis": total_new_analysis_cost,
            "Time" : time.time()-start_time,
    }

    # Log the complete response in a single entry
    logger.info(f"Field extraction completed - Field: 'Industries' | Response: {json.dumps(result, ensure_ascii=False)}")

    return result
