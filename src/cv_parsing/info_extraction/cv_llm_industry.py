from src.google_services.sheets import read_specific_columns, write_specific_columns
from src.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler, extract_and_parse_token_section

import pandas as pd
from typing import List, Tuple, Dict, Any
from src.logger import logger

def parse_single_industry_analysis(llm_response: str) -> Dict[str, Any]:
    """
    Parses the model's response for a single proposed industry.
    Extracts the analysis, recommendation, and token/cost information.

    Args:
        llm_response (str): Full model response, including the token usage section.

    Returns:
        Dict[str, Any]: Dictionary with keys:
            - "proposed_industry": proposed industry name,
            - "pros": list of pros arguments,
            - "cons": list of cons arguments,
            - "justification": justification sentence,
            - "recommendation": "Add" or {"overlaps_with": "Existing Industry Name"},
            - "cost": cost of the API call (float, if available).
    """
    # Split the response into sections, extract token usage and cost
    cleaned_response, token_data = extract_and_parse_token_section(
        response=llm_response,
        additional_key_text="",
        add_tokens_info=True
    )

    result = {
        "proposed_industry": None,
        "pros": [],
        "cons": [],
        "justification": None,
        "recommendation": None,
        "cost": None
    }

    # Extract cost from token data
    if "Cost" in token_data:
        result["cost"] = float(token_data["Cost"].replace("$", ""))

    lines = cleaned_response.strip().split('\n')

    # Extract proposed industry name
    proposed_line = next((line for line in lines if line.startswith("### Analysis of:")), None)
    if proposed_line:
        result["proposed_industry"] = proposed_line.replace("### Analysis of:", "").strip()

    # Extract pros arguments
    pros_start = next((i for i, line in enumerate(lines) if line.startswith("**Arguments For (Pros):**")), None)
    if pros_start:
        cons_start = next((i for i, line in enumerate(lines) if line.startswith("**Arguments Against (Cons):**")), None)
        pros_lines = lines[pros_start + 1:cons_start] if cons_start else []
        result["pros"] = [line.strip().lstrip('- ').strip() for line in pros_lines if line.strip() and not line.startswith('**')]

    # Extract cons arguments
    cons_start = next((i for i, line in enumerate(lines) if line.startswith("**Arguments Against (Cons):**")), None)
    if cons_start:
        justification_start = next((i for i, line in enumerate(lines) if line.startswith("**Justification:**")), None)
        cons_lines = lines[cons_start + 1:justification_start] if justification_start else []
        result["cons"] = [line.strip().lstrip('- ').strip() for line in cons_lines if line.strip() and not line.startswith('**')]

    # Extract justification
    justification_line = next((line for line in lines if line.startswith("**Justification:**")), None)
    if justification_line:
        result["justification"] = justification_line.replace("**Justification:**", "").strip()

    # Extract recommendation
    recommendation_line = next((line for line in lines if line.startswith("**Final Recommendation:**")), None)
    if recommendation_line:
        rec_text = recommendation_line.replace("**Final Recommendation:**", "").strip()
        if rec_text.startswith("Add"):
            result["recommendation"] = "Add"
        elif "Overlaps with:" in rec_text:
            overlaps_with = rec_text.replace("Overlaps with:", "").strip()
            result["recommendation"] = {"overlaps_with": overlaps_with}

    return result


def process_proposed_industries(
    llm_handler: LLMHandler,
    existing_industries_list: List[str],
    proposed_industries: List[str],
    model: str = "gpt-4.1-nano",
    service=None  # Google Sheets service for writing updates
) -> Tuple[List[str], float]:
    """
    Processes proposed industries, updates the master list in Google Sheets,
    and returns a combined list of industries to add and overlaps, along with the total cost.

    Args:
        llm_handler (LLMHandler): Instance of LLMHandler for API calls.
        existing_industries_list (List[str]): List of existing industries.
        proposed_industries (List[str]): List of proposed industries to analyze.
        model (str): Model name for LLMHandler.
        service: Google Sheets service for writing updates.

    Returns:
        Tuple[List[str], float]:
            - Combined list of industries to add and overlaps.
            - Total cost of API calls.
    """
    if len(proposed_industries) == 0:
        return [], 0
    print("!!!!!!! proposed_industries:", str(proposed_industries))
    # Convert industries_list to a formatted string for the prompt
    industries_str = f'"{", ".join(existing_industries_list)}"'

    to_add = []  # List of industries to add
    overlaps = []  # List of industries that overlap with existing ones
    total_cost = 0.0  # Total cost of all API calls

    for proposed in proposed_industries:
        # Prepare the prompt for analyzing the current proposed industry
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a senior data architect and taxonomist. "
                    "Your task is to analyze a single proposed industry for inclusion in a master list of IT project industries. "
                    "Your analysis must be precise, logical, and strictly follow the output format."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Current master list of industries: {industries_str}\n\n"
                    "The master list must adhere to two principles: "
                    "1. **Non-Overlapping**: Each industry must represent a unique domain. "
                    "2. **Comprehensive**: The list must cover most IT project domains."
                    f"Analyze the following proposed industry to include in master list: **{proposed}**\n\n"
                    "**Output Format:**\n"
                    f"### Analysis of: {proposed}\n"
                    "**Arguments For (Pros):**\n- ...\n"
                    "**Arguments Against (Cons):**\n- ...\n"
                    "**Justification:** ...\n"
                    "**Final Recommendation:** Add / Overlaps with: [Existing Industry Name]"
                )
            }
        ]
        # Get the model's response
        response = llm_handler.get_answer(prompt, model=model)
        if response is None:
            logger.error(f"Failed to get response for proposed industry: {proposed}")
            continue  # Skip if the request failed

        # Parse the main response
        analysis = parse_single_industry_analysis(response)

        # Add the cost of the current request to the total cost
        if "Cost" in analysis:
            total_cost += float(analysis["Cost"])

        # Update results
        if analysis["recommendation"] == "Add":
            to_add.append(proposed)
        elif isinstance(analysis["recommendation"], dict):
            overlap_industry = analysis["recommendation"]["overlaps_with"]
            if overlap_industry in existing_industries_list:
                overlaps.append(overlap_industry)
            else:
                logger.error(
                    f"Overlap industry '{overlap_industry}' for '{proposed}' "
                    f"not found in the master list: {existing_industries_list}"
                )

    # Combine existing and new industries, sort, and remove duplicates
    updated_industries = sorted(list(set(existing_industries_list + to_add)))

    # Write the updated list to Google Sheets
    if service:
        updated_df = pd.DataFrame({"Industry Values": updated_industries})
        write_specific_columns(df=updated_df, sheet_name="values", service=service)

    # Return combined list (to_add + overlaps) and total cost
    combined_list = to_add + overlaps
    return combined_list, total_cost


def parse_llm_cv_industry_response(llm_response: str, add_tokens_info: bool = False) -> dict:
    """
    Parses the LLM response for matched and new industries.
    Extracts reasoning (if add_tokens_info=True), matched/new industries, and cost information.
    Args:
        llm_response (str): Model's response with "Reasoning:" and "Final Answer:" sections.
        add_tokens_info (bool): If True, includes reasoning and uses "Cost" as the cost key.
    Returns:
        dict: Dictionary with keys:
            - "Reasoning about Industries": Detailed reasoning (only if add_tokens_info=True).
            - "Matched": List of matched industries (empty list if none).
            - "New": List of new industries (empty list if none).
            - "Cost" or "Cost_of_Industries_CV_extraction": Cost of the API call (always included).
            - All keys from tokens_data (only if add_tokens_info=True).
    """
    # Extract and clean the response (remove token section)
    response, token_data = extract_and_parse_token_section(
        response=llm_response,
        additional_key_text="",
        add_tokens_info=add_tokens_info
    )

    result = {"Matched": [], "New": []}
    # Extract reasoning if add_tokens_info=True
    if add_tokens_info:
        lines = response.strip().split('\n')
        reasoning_lines = []
        for line in lines:
            if line.startswith("**Final Answer:**"):
                break
            reasoning_lines.append(line)
        result["Reasoning about Industries"] = "\n".join(reasoning_lines).strip()
    # Parse matched and new industries from "Final Answer:" section
    final_answer_section = False
    for line in response.strip().split('\n'):
        if line.startswith("**Final Answer:**"):
            final_answer_section = True
            continue
        if final_answer_section:
            if line.startswith("Matched Industries:"):
                matched_str = line.replace("Matched Industries:", "").strip()
                if matched_str != "No industries identified":
                    matched_industries = [
                        ind.strip().strip('"\'')
                        for ind in matched_str.split(',')
                        if ind.strip()
                    ]
                    result["Matched"] = matched_industries
            elif line.startswith("New Industries:"):
                new_str = line.replace("New Industries:", "").strip()
                new_industries = [
                    ind.strip().strip('"\'')
                    for ind in new_str.split(',')
                    if ind.strip()
                ]
                result["New"] = new_industries
    # Extract cost from cost_data (always included)
    if "Cost" in token_data:
        if add_tokens_info:
            # Append full tokens_data only if add_tokens_info=True
            result.update(token_data)
        else:
            cost = float(token_data["Cost"].replace("$", ""))
            result["Cost_of_Industries_CV_extraction"] = cost  # Working mode: detailed key
    return result

def extract_cv_industry(cv: str, llm_handler: LLMHandler, model="gpt-4.1-mini", add_tokens_info: bool = False):
    industries_list = list(read_specific_columns(['Industry Values'], 'values')['Industry Values'])
    industries = '", "'.join(industries_list)
    industries = f'"{industries}"'

    # Define the prompt for the language model
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert industry analyst specializing in data categorization. "
                "Your task is to analyze project descriptions from a resume and accurately classify them against a predefined list of industries. "
                "**First, explain your reasoning step-by-step in bullet points.** "
                "Then, return the final output in the required format."
            )
        },
        {
            "role": "user",
            "content": (
                "Analyze the projects in the following resume to identify their industries. "
                "**Explain your reasoning step-by-step**, then return the final output in the required format.\n\n"
                f"**Predefined list of accepted industries:** {industries}\n\n"
                "**Your internal thought process for this task must be:**\n"
                "1. Read through all project descriptions to understand their core function and domain.\n"
                "2. For each project, identify one or more potential industries.\n"
                "3. For each identified industry, reason if it truly fits the project's description.\n"
                "4. Compare every identified industry against the predefined list.\n"
                "5. Compile two master lists: one for matched industries, and one for new industries. Remove all duplicates.\n\n"
                "**Output Instructions:**\n"
                "1. **Reasoning:** [Your step-by-step analysis in bullet points].\n"
                "2. **Final Answer:** [Two lines: 'Matched Industries: ...' and 'New Industries: ...'].\n\n"
                "**Example Output:**\n"
                "Reasoning:\n"
                "- Project 1 describes financial software → Matched to 'FinTech'.\n"
                "- Project 2 mentions healthcare analytics → Matched to 'HealthTech'.\n"
                "- Project 3 describes a new domain 'AgriTech' → Added to New Industries.\n"
                "Final Answer:\n"
                "Matched Industries: FinTech, HealthTech\n"
                "New Industries: AgriTech\n\n"
                "**Here is the CV:**\n"
                f"{cv}"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = len(cv)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
    print(response)
    # Parse the response from the LLM
    extracted_data = parse_llm_cv_industry_response(response, add_tokens_info=add_tokens_info)
    # Move non-existent industries from "Matched" to "New"
    industries_set = set(industries_list)
    extracted_data["New"] = list(set(extracted_data["New"]).union(
        [ind for ind in extracted_data["Matched"] if ind not in industries_set]
    ))
    extracted_data["Matched"] = [ind for ind in extracted_data["Matched"] if ind in industries_set]
    print(extracted_data)

    to_add, process_new_cost = process_proposed_industries(
                        existing_industries_list=industries_list,
                        proposed_industries=extracted_data["New"]
                )
    final_cv_industries_list = extracted_data["Matched"] + to_add
    result = {
            "Industry" : ', '.join(final_cv_industries_list),
            "Cost_of_industry_CV_extraction": extracted_data['Cost'],
            "Cost_of_new_industries_analysis": process_new_cost
            }
    return result

