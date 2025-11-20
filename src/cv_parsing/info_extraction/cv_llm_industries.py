import pandas as pd

from src.cv_parsing.info_extraction.cv_llm_it_domains import format_it_domains_reasoning, \
    analyze_single_project_it_domains
# from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler


import random
from typing import Literal, Union, Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def create_project_industry_model(predefined_industries: List[str]) -> type[BaseModel]:
    """
    Creates a Pydantic model for analyzing a single project's industry.
    """
    IndustryType = Literal[*predefined_industries]

    class ProjectIndustryAnalysis(BaseModel):
        project_name: str = Field(description="Name or description of the project")
        supporting_evidence: List[str] = Field(description="Phrases from the resume supporting the industry choice")
        has_enough_info: bool = Field(description="Whether there is enough information to determine the industry")
        potential_industries: List[str] = Field(description="List of all potential industries from the predefined list that could fit the project")
        reasoning: str = Field(description="Reasoning for selecting the most suitable industry from potential_industries")
        has_suitable_industry: bool = Field(description="Whether there is a suitable industry in the predefined list")
        selected_industry: Optional[IndustryType] = Field(default=None, description="Most suitable industry selected from potential_industries (None if no suitable industry or not enough info)")
        new_industry: Optional[str] = Field(default=None, description="Proposed new industry if no suitable industry was found in the predefined list")

    return ProjectIndustryAnalysis



def analyze_project_industry_and_it_domains(
    project_text: str,
    predefined_it_domains: List[str],
    predefined_industries: List[str],
    llm_handler: Any,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Analyzes both IT domains and industry for a single project.

    Args:
        project_text: Text of the project to analyze.
        predefined_it_domains: List of predefined IT domains.
        predefined_industries: List of predefined industries.
        llm_handler: Handler for interacting with the LLM.
        model: Name of the model to use for analysis.

    Returns:
        Dictionary with the project's IT domains and industry analysis.
    """
    # Step 1: Analyze IT domains
    it_domains_result = analyze_single_project_it_domains(
        project_text=project_text,
        predefined_it_domains=predefined_it_domains,
        llm_handler=llm_handler,
        model=model
    )

    # Extract identified IT domains for the industry prompt
    identified_it_domains = []
    for domain in it_domains_result["it_domains"]:
        selected_domain = domain.get("selected_it_domain")
        new_domain = domain.get("new_it_domain")
        if selected_domain:
            identified_it_domains.append(selected_domain)
        elif new_domain:
            identified_it_domains.append(f"NEW: {new_domain}")

    # Step 2: Analyze industry using the identified IT domains
    industry_prompt = generate_industry_prompt(
        project_text=project_text,
        predefined_industries=predefined_industries,
        it_domains=identified_it_domains
    )

    # Create Pydantic model for industry analysis
    ProjectIndustryModel = create_project_industry_model(predefined_industries)

    # Get industry analysis from LLM
    industry_response = llm_handler.get_answer(
        prompt=industry_prompt,
        model=model,
        response_format=ProjectIndustryModel,
    )

    industry_analysis = industry_response["parsed"].model_dump()
    industry_analysis["usage"] = industry_response["usage"]
    industry_analysis["cost"] = industry_response["cost"]

    # Step 3: Combine results
    result = {
        "project_name": it_domains_result["project_name"],
        "it_domains": {
            "analysis": it_domains_result["it_domains"],
            "reasoning": format_it_domains_reasoning(it_domains_result),
            "usage": it_domains_result["usage"],
            "cost": it_domains_result["cost"]
        },
        "industry": {
            "analysis": industry_analysis,
            "reasoning": format_project_reasoning(industry_analysis),
            "usage": industry_response["usage"],
            "cost": industry_response["cost"]
        }
    }

    return result



def format_project_reasoning(project: dict) -> str:
    lines = [
        f"Project: {project['project_name']}",
        f"Supporting evidence: {', '.join(project['supporting_evidence'])}",
        f"Has enough info: {'Yes' if project['has_enough_info'] else 'No'}"
    ]
    # if not project['has_enough_info']:
    #     return "\n".join(lines)
    lines.extend([
        f"Potential industries: {', '.join(project['potential_industries'])}",
        f"Has suitable industry: {'Yes' if project['has_suitable_industry'] else 'No'}",
        f"Reasoning: {project['reasoning']}"
    ])
    if project['selected_industry'] is not None:
        lines.append(f"Selected industry: {project['selected_industry']}")
    else:
        if project.get('new_industry') is not None:
            lines.append(f"New proposed industry: {project['new_industry']}")
    return "\n".join(lines)


def generate_industry_prompt(
    project_text: str,
    predefined_industries: List[str],
    it_domains: List[str]
) -> List[Dict[str, str]]:
    """
    Generates a prompt for extracting the industry of a project,
    considering the previously identified IT domains.

    Args:
        project_text: Text of the project to analyze.
        predefined_industries: List of predefined industries.
        it_domains: List of IT domains already identified for the project.

    Returns:
        A list of dictionaries representing the prompt messages.
    """
    # Format predefined industries as a string
    industries_str = ", ".join(f'"{industry}"' for industry in predefined_industries)

    # Select random examples for clarity
    industry_examples = random.sample(predefined_industries, min(3, len(predefined_industries)))
    industry_examples_str = ", ".join(f'"{example}"' for example in industry_examples)

    # Prepare IT domains examples if available
    it_domains_examples = []
    if len(it_domains) >= 2:
        it_domains_examples = random.sample(it_domains, 2)
    elif len(it_domains) == 1:
        it_domains_examples = it_domains
    it_domains_examples_str = ", ".join(f'"{domain}"' for domain in it_domains_examples)

    # Define the system content with IT domains note if applicable
    system_content = (
        "You are an expert in resume analysis. "
        "Your task is to analyze the project and determine its industry in two steps:\n"
        "This helps to understand the candidate's expertise and knowledge in specific domains.\n"
        "1. List **all potential industries** from the predefined list that could fit the project.\n"
        "2. Explain your reasoning and select the **most specific and accurate industry** from the list.\n"
        "Follow these rules:\n"
        "- Always prefer the most specific industry.\n"
        "- If there is not enough information to determine the industry, set `has_enough_info` to `False`.\n"
        "- If there is no suitable industry in the predefined list, set `has_suitable_industry` to `False` and suggest a new industry in `new_industry`.\n"
        "- Provide a clear explanation for your choice."
    )

    # Add IT domains note if applicable
    if it_domains:
        system_content += (
            f"\nNote: IT domains (such as {it_domains_examples_str}, etc.) are NOT industries. "
            f"Focus on the **industry** (e.g., {industry_examples_str}, etc.)."
        )
        it_domains_str = ", ".join(f'"{domain}"' for domain in it_domains)
        it_domains_str = f"The following IT domains have already been identified for this project: {it_domains_str}.\n"
    else:
        it_domains_str = ""

    # Define the prompt
    prompt = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": (
                f"Analyze the following project:\n\n"
                f"**Predefined list of industries:** {industries_str}\n\n"
                "Follow these steps:\n"
                f"1. Name the project.\n"
                f"2. List phrases from the resume supporting the industry choice (`supporting_evidence`).\n"
                f"3. Set `has_enough_info` to `True` or `False` (whether there is enough information to determine the industry).\n"
                f"4. List all potential industries from the predefined list (`potential_industries`).\n"
                f"5. Explain your reasoning (`reasoning`).\n"
                f"6. Set `has_suitable_industry` to `True` or `False` (whether there is a suitable industry in the predefined list).\n"
                f"7. Select the most suitable industry (`selected_industry`) or leave it empty if no suitable industry or not enough info.\n"
                f"8. If no suitable industry, suggest a new industry in `new_industry`.\n"
                f"**Project:**\n{project_text}"
                f"\n{it_domains_str}."
            )
        }
    ]

    return prompt


def extract_cv_domains_and_industries(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts and analyzes industries from a resume using parallel processing.
    """
    start_time = time.time()
    values_df = read_specific_columns(['Industries Values', 'IT Domains Values'], 'values')
    predefined_industries = [val.strip() for val in values_df['Industries Values'].tolist() if val and pd.notna(val)]
    predefined_it_domains = [val.strip() for val in values_df['IT Domains Values'].tolist() if val and pd.notna(val)]

    # Extract projects from the resume
    projects_list = get_section_for_field(cv_sections, "Projects")

    # Initialize counters
    total_it_domains_completion_tokens = 0
    total_it_domains_prompt_tokens = 0
    total_it_domains_cost = 0.0
    total_industries_completion_tokens = 0
    total_industries_prompt_tokens = 0
    total_industries_cost = 0.0

    # Analyze each project in parallel
    projects_analysis = []
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                analyze_project_industry_and_it_domains,
                project_text,
                predefined_it_domains,
                predefined_industries,
                llm_handler,
                model
            )
            for project_text in projects_list
        ]

        for future in as_completed(futures):
            result = future.result()
            projects_analysis.append(result)
            # Update IT domains counters
            total_it_domains_completion_tokens += result["it_domains"]["usage"].completion_tokens
            total_it_domains_prompt_tokens += result["it_domains"]["usage"].prompt_tokens
            total_it_domains_cost += result["it_domains"]["cost"]["total_cost"]
            # Update industries counters
            total_industries_completion_tokens += result["industry"]["usage"].completion_tokens
            total_industries_prompt_tokens += result["industry"]["usage"].prompt_tokens
            total_industries_cost += result["industry"]["cost"]["total_cost"]

    # Extract industries
    all_industries = []
    for project in projects_analysis:
        industry_name = project["industry"]["analysis"]['selected_industry']
        new_industry = project["industry"]["analysis"]['selected_industry']
        if industry_name is not None:
            if industry_name not in all_industries:
                all_industries.append(industry_name)
        elif new_industry is not None:
            new_industry = f"NEW {new_industry}"
            if new_industry not in all_industries:
                all_industries.append(new_industry)
    industries_str = ", ".join(all_industries)
    print(industries_str)


    # Extract IT domains
    all_it_domains = []
    for project in projects_analysis:
        for domain in project["it_domains"]["analysis"]:
            if domain.get("selected_it_domain") is not None:
                if domain["selected_it_domain"] not in all_it_domains:
                    all_it_domains.append(domain["selected_it_domain"])
            elif domain.get("new_it_domain") is not None:
                new_it_domain = f"NEW {domain['new_it_domain']}"
                if new_it_domain not in all_it_domains:
                    all_it_domains.append(new_it_domain)

    it_domains_str = ", ".join(all_it_domains)

    # Build the reasoning text
    industries_reasoning_lines = []
    for project in projects_analysis:
        industries_reasoning_lines.append(format_project_reasoning(project["industry"]["analysis"]))
        industries_reasoning_lines.append("-" * 50)
    industries_reasoning_text = "\n".join(industries_reasoning_lines)

    # Build the reasoning text for IT domains
    it_domains_reasoning_lines = []
    for project in projects_analysis:
        it_domains_reasoning_lines.append(project["it_domains"]["reasoning"])
        it_domains_reasoning_lines.append("-" * 50)
    it_domains_reasoning_text = "\n".join(it_domains_reasoning_lines)

    # Build the result dictionary
    result = {
        # Industries fields
        "Industries": industries_str,
        "Reasoning about Industries": industries_reasoning_text,
        "Model of Industries CV extraction": model,
        "Completion Tokens of Industries CV extraction": str(total_industries_completion_tokens),
        "Prompt Tokens of Industries CV extraction": str(total_industries_prompt_tokens),
        "Cost of Industries CV extraction": total_industries_cost,
        "Cost of new industries analysis": 0,
        # IT Domains fields
        "IT Domains": it_domains_str,
        "Reasoning about IT Domains": it_domains_reasoning_text,
        "Model of IT Domains CV extraction": model,
        "Completion Tokens of IT Domains CV extraction": str(total_it_domains_completion_tokens),
        "Prompt Tokens of IT Domains CV extraction": str(total_it_domains_prompt_tokens),
        "Cost of IT Domains CV extraction": total_it_domains_cost,
        # Common fields
        "Time": time.time() - start_time,
    }

    return result
