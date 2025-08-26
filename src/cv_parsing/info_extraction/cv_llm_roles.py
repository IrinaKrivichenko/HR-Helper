from typing import List, Tuple

import pandas as pd

from src.google_services.sheets import read_specific_columns, write_specific_columns
from src.logger import logger
from src.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler, extract_and_parse_token_section

def parse_single_role_analysis(response: str) -> dict:
    """
    Parses the model's response for a single proposed role analysis.
    Extracts the analysis, recommendation, and token/cost information.

    Args:
        response (str): Full model response, including the token usage section.

    Returns:
        dict: Dictionary with keys:
            - "proposed_role": proposed role name,
            - "pros": list of pros arguments,
            - "cons": list of cons arguments,
            - "justification": justification sentence,
            - "recommendation": "Add" or {"overlaps_with": "Existing Role Name"},
            - "cost": cost of the API call (float, if available).
    """
    # Split the response into sections, extract token usage and cost
    cleaned_response, token_data = extract_and_parse_token_section(
        response=response,
        additional_key_text="",
        add_tokens_info=True
    )

    result = {
        "proposed_role": None,
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

    # Extract proposed role name
    proposed_line = next((line for line in lines if line.startswith("### Analysis of:")), None)
    if proposed_line:
        result["proposed_role"] = proposed_line.replace("### Analysis of:", "").strip()

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

def process_proposed_roles(
    llm_handler: LLMHandler,
    roles_list: List[str],
    proposed_roles: List[str],
    model: str = "gpt-4.1-mini",
    service=None  # Google Sheets service for writing updates
) -> Tuple[List[str], float]:
    """
    Processes proposed roles, updates the master list in Google Sheets,
    and returns a combined list of roles to add and overlaps, along with the total cost.

    Args:
        llm_handler (LLMHandler): Instance of LLMHandler for API calls.
        roles_list (List[str]): List of existing roles.
        proposed_roles (List[str]): List of proposed roles to analyze.
        model (str): Model name for LLMHandler.
        service: Google Sheets service for writing updates.

    Returns:
        Tuple[List[str], float]:
            - Combined list of roles to add and overlaps.
            - Total cost of API calls.
    """
    if len(proposed_roles) == 0:
        return [], 0
    print("!!!!!!! proposed_roles:", str(proposed_roles))
    # Convert roles_list to a formatted string for the prompt
    roles_str = f'"{", ".join(roles_list)}"'

    to_add = []  # List of roles to add
    overlaps = []  # List of roles that overlap with existing ones
    total_cost = 0.0  # Total cost of all API calls

    for proposed in proposed_roles:
        # Prepare the prompt for analyzing the current proposed role
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an expert technical recruiter and role analyst. "
                    "Your task is to accurately identify all professional roles a candidate has performed based on their resume, "
                    "comparing them against a predefined list. You must be precise and strictly follow the output format."
            )
            },
            {
                "role": "user",
                "content": (
                    f"Current master list of roles: {roles_str}\n\n"
                    "The master list must adhere to two principles: "
                    "1. **Non-Overlapping**: Each role must represent a unique function. "
                    "2. **Comprehensive**: The list must cover most IT roles."
                    f"Analyze the following proposed role to include in master list: **{proposed}**\n\n"
                    "**Output Format:**\n"
                    f"### Analysis of: {proposed}\n"
                    "**Arguments For (Pros):**\n- ...\n"
                    "**Arguments Against (Cons):**\n- ...\n"
                    "**Justification:** ...\n"
                    "**Final Recommendation:** Add / Overlaps with: [Existing Role Name]"
                )
            }
        ]

        # Get the model's response
        response = llm_handler.get_answer(prompt, model=model)
        if response is None:
            logger.error(f"Failed to get response for proposed role: {proposed}")
            continue  # Skip if the request failed

        # Parse the main response
        analysis = parse_single_role_analysis(response)

        # Add the cost of the current request to the total cost
        if "Cost" in analysis:
            total_cost += float(analysis["Cost"])

        # Update results
        if analysis["recommendation"] == "Add":
            to_add.append(proposed)
        elif isinstance(analysis["recommendation"], dict):
            overlap_role = analysis["recommendation"]["overlaps_with"]
            if overlap_role in roles_list:
                overlaps.append(overlap_role)
            else:
                logger.error(
                    f"Overlap role '{overlap_role}' for '{proposed}' "
                    f"not found in the master list: {roles_list}"
                )

    # Combine existing and new roles, sort, and remove duplicates
    updated_roles = sorted(list(set(roles_list + to_add)))

    # Write the updated list to Google Sheets
    if service:
        updated_df = pd.DataFrame({"Role Values": updated_roles})
        write_specific_columns(df=updated_df, sheet_name="values", service=service)

    # Return combined list (to_add + overlaps) and total cost
    combined_list = to_add + overlaps
    return combined_list, total_cost


def parse_llm_cv_roles_response(llm_response: str, add_tokens_info: bool = False) -> dict:
    """
    Parses the LLM response for a CV roles analysis.
    Extracts reasoning (if add_tokens_info=True), matched/new roles, and cost information.
    Args:
        llm_response (str): Model's response with "Reasoning:" and "Final Answer:" sections.
        add_tokens_info (bool): If True, includes reasoning and uses "Cost" as the cost key.
    Returns:
        dict: Dictionary with keys:
            - "Reasoning about Roles": Detailed reasoning (only if add_tokens_info=True).
            - "Matched": List of matched roles (empty list if none).
            - "New": List of new roles (empty list if none).
            - "Cost" or "Cost_of_Roles_CV_extraction": Cost of the API call (always included).
            - All keys from tokens_data (only if add_tokens_info=True).
    """
    # Extract and clean the response (remove token section)
    cleaned_response, token_data = extract_and_parse_token_section(
        response=llm_response,
        additional_key_text=" cv_roles",
        add_tokens_info=add_tokens_info
    )
    result = {"Matched": [], "New": []}
    # Extract reasoning if add_tokens_info=True
    if add_tokens_info:
        lines = cleaned_response.strip().split('\n')
        reasoning_lines = []
        for line in lines:
            if line.startswith("Final Answer:"):
                break
            reasoning_lines.append(line)
        result["Reasoning about Roles"] = "\n".join(reasoning_lines).strip()
    # Parse matched and new roles from "Final Answer:" section
    final_answer_section = False
    for line in cleaned_response.strip().split('\n'):
        if line.startswith("Final Answer:"):
            final_answer_section = True
            continue
        if final_answer_section:
            if line.startswith("Matched Roles:"):
                matched_roles_str = line.replace("Matched Roles:", "").strip()
                if matched_roles_str != "No matched roles":
                    result["Matched"] = [role.strip() for role in matched_roles_str.split(',')]
            elif line.startswith("New Roles:"):
                new_roles_str = line.replace("New Roles:", "").strip()
                if new_roles_str != "No new roles":
                    result["New"] = [role.strip() for role in new_roles_str.split(',')]
    # Extract cost from token_data (always included)
    if "Cost" in token_data:
        if add_tokens_info:
            # Append full tokens_data only if add_tokens_info=True
            result.update(token_data)
        else:
            cost = float(token_data["Cost"].replace("$", ""))
            result["Cost_of_Roles_CV_extraction"] = cost  # Working mode: detailed key
    return result


def extract_cv_roles(cv: str, llm_handler: LLMHandler, model="gpt-4.1-mini", add_tokens_info: bool = False):
    roles_list = list(read_specific_columns(['Role Values'], 'values')['Role Values'])
    roles = '", "'.join(roles_list)
    roles = f'"{roles}"'

    # Define the prompt for the language model
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert technical recruiter and role analyst. "
                "Your function is to accurately identify all professional roles a candidate has performed based on their resume. "
                "**First, explain your reasoning step-by-step in bullet points.** "
                "Then, return the final output in the required format."
            )
        },
        {
            "role": "user",
            "content": (
                "Analyze the following resume to identify all IT roles the candidate has performed. "
                "**Explain your reasoning step-by-step**, then return the final output in the required format.\n\n"
                "**Predefined list of accepted roles:**\n"
                f"{roles}\n\n"
                "**Your internal thought process for this task must be:**\n"
                "1. Scan the entire resume, paying close attention to job titles and descriptions of responsibilities in projects.\n"
                "2. **Crucial Rule 1: Ignore Seniority.** Focus on the core function of the role. Explicitly ignore prefixes like 'Senior', 'Junior', 'Middle', or 'Principle'.\n"
                "3. **Crucial Rule 2: Be Specific with Developers.** Map developer roles to the specific programming language mentioned in the project context (e.g., 'Python Developer').\n"
                "4. **Crucial Rule 3: Map Responsibilities to Roles.** Analyze task descriptions to identify roles even if they are not explicitly named.\n"
                "5. Compile two master lists: one for roles that matched the predefined list, and one for new roles.\n\n"
                "**Output Instructions:**\n"
                "1. **Reasoning:** [Your step-by-step analysis in bullet points].\n"
                "2. **Final Answer:** [Two lines: 'Matched Roles: ...' and 'New Roles: ...'].\n\n"
                "**Example Output:**\n"
                "Reasoning:\n"
                "- Found 'Go Developer' in job title → Added to Matched Roles.\n"
                "- Found 'DevOps Engineer' in responsibilities but not in predefined list → Added to New Roles.\n"
                "Final Answer:\n"
                "Matched Roles: Go Developer, Engineering Manager\n"
                "New Roles: DevOps Engineer\n\n"
                "**Here is the CV:**\n"
                f"{cv}"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = max(len(cv), 200)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
    print(response)

    # Parse the response from the LLM
    extracted_data = parse_llm_cv_roles_response(response)
    # Move non-existent roles from "Matched" to "New"
    roles_set = set(roles_list)
    extracted_data["New"] = list(set(extracted_data["New"]).union(
        [ind for ind in extracted_data["Matched"] if ind not in roles_set]
    ))
    extracted_data["Matched"] = [ind for ind in extracted_data["Matched"] if ind in roles_set]
    print(extracted_data)

    # Process new roles
    to_add, process_new_cost = process_proposed_roles(
        llm_handler=llm_handler,
        roles_list=roles,
        proposed_roles=extracted_data["New"],
        model=model
    )

    # Combine matched and new roles
    final_cv_roles_list = extracted_data["Matched"] + to_add

    # Prepare the result
    result = {
        "Role": ', '.join(final_cv_roles_list),
        "Cost_of_Role_CV_extraction": extracted_data.get('Cost', 0),
        "Cost_of_new_roles_analysis": process_new_cost
    }

    return result
