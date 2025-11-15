

# from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import LLMHandler

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


def analyze_single_project(
    project_text: str,
    predefined_industries: List[str],
    llm_handler: LLMHandler,
    model: str
) -> Dict[str, Any]:
    """
    Analyzes a single project and returns its industry analysis.
    """
    ProjectIndustryModel = create_project_industry_model(predefined_industries)
    prompt = generate_project_prompt(project_text, predefined_industries)

    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        response_format=ProjectIndustryModel,
    )

    project_analysis = response["parsed"].model_dump()
    project_analysis["usage"] = response["usage"]
    project_analysis["cost"] = response["cost"]

    return project_analysis


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


def generate_project_prompt(project_text: str, predefined_industries: List[str]) -> List[dict]:
    """
    Generates a prompt for LLM to analyze a single project in two steps.
    """
    industries_str = ", ".join(f'"{industry}"' for industry in predefined_industries)
    prompt = [
        {
            "role": "system",
            "content": (
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
        },
        {
            "role": "user",
            "content": (
                f"Analyze the following project:\n\n"
                f"**Predefined list of industries:** {industries_str}\n\n"
                f"**Project:**\n{project_text}\n\n"
                "Follow these steps:\n"
                f"1. Name the project.\n"
                f"2. List phrases from the resume supporting the industry choice (`supporting_evidence`).\n"
                f"3. Set `has_enough_info` to `True` or `False` (whether there is enough information to determine the industry).\n"
                f"4. List all potential industries from the predefined list (`potential_industries`).\n"
                f"5. Explain your reasoning (`reasoning`).\n"
                f"6. Set `has_suitable_industry` to `True` or `False` (whether there is a suitable industry in the predefined list).\n"
                f"7. Select the most suitable industry (`selected_industry`) or leave it empty if no suitable industry or not enough info.\n"
                f"8. If no suitable industry, suggest a new industry in `new_industry`."
            )
        }
    ]
    return prompt


def extract_cv_industries(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts and analyzes industries from a resume using parallel processing.
    """
    start_time = time.time()
    predefined_industries = list(read_specific_columns(['Industries Values'], 'values')['Industries Values'])

    # Extract projects from the resume
    projects_list = get_section_for_field(cv_sections, "Projects")

    # Analyze each project in parallel
    projects_analysis = []
    total_completion_tokens = 0
    total_prompt_tokens = 0
    total_cost = 0.0

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                analyze_single_project,
                project_text,
                predefined_industries,
                llm_handler,
                model
            )
            for project_text in projects_list
        ]

        for future in as_completed(futures):
            result = future.result()
            projects_analysis.append(result)
            total_completion_tokens += result["usage"].completion_tokens
            total_prompt_tokens += result["usage"].prompt_tokens
            total_cost += result["cost"]["total_cost"]

    # Extract industries
    all_industries = []
    for project in projects_analysis:
        if project['selected_industry'] is not None:
            if project['selected_industry'] not in all_industries:
                all_industries.append(project['selected_industry'])
        elif project['new_industry'] is not None:
            new_industry = f"NEW {project['new_industry']}"
            if new_industry not in all_industries:
                all_industries.append(new_industry)
    industries_str = ", ".join(all_industries)

    # Build the reasoning text
    reasoning_lines = []
    for project in projects_analysis:
        reasoning_lines.append(format_project_reasoning(project))
        reasoning_lines.append("-" * 50)  # Разделитель
    # if new_industries_reasoning:
    #     reasoning_lines.append("\nNew Industries Analysis:\n")
    #     reasoning_lines.append(new_industries_reasoning)
    reasoning_text = "\n".join(reasoning_lines)

    # Build the result dictionary
    result = {
        "Industries": ", ".join(industries_str),
        "Reasoning about Industries": reasoning_text,
        "Model of_Industries_CV_extraction": model,
        "Completion Tokens of_Industries_CV_extraction": str(total_completion_tokens),
        "Prompt Tokens of_Industries_CV_extraction": str(total_prompt_tokens),
        "Cost_of_industries_CV_extraction": total_cost,
        "Cost_of_new_industries_analysis": 0,
        "Time": time.time() - start_time,
    }

    return result

    #     for future in as_completed(futures):
    #         result = future.result()
    #         projects_analysis.append(result)
    #         total_completion_tokens += result["usage"].completion_tokens
    #         total_prompt_tokens += result["usage"].prompt_tokens
    #         total_cost += result["cost"]["total_cost"]
    #
    # # Extract all unique industries
    # all_industries = [project["selected_industry"] for project in projects_analysis]
    # unique_industries = list(set(all_industries))
    #
    # # Separate predefined and new industries
    # predefined_set = set(predefined_industries)
    # new_industries = [industry for industry in unique_industries if industry not in predefined_set]
    # found_industries = [industry for industry in unique_industries if industry in predefined_set]
    #
    # # Process new industries
    # approved_industries, new_industries_reasoning, new_analysis_cost = process_proposed_industries(
    #     llm_handler=llm_handler,
    #     existing_industries_list=predefined_industries,
    #     proposed_industries=new_industries,
    #     model=model
    # )
    #
    # # Combine all industries
    # approved_industries_clean = [industry.replace("NEW ", "") for industry in approved_industries]
    # final_industries = list(set(found_industries).union(set(approved_industries_clean)))
    #
    # # Build the reasoning text
    # reasoning_lines = []
    # for project in projects_analysis:
    #     reasoning_lines.append(
    #         f"Project: {project['project_name']}\n"
    #         f"Potential industries: {', '.join(project['potential_industries'])}\n"
    #         f"Reasoning: {project['reasoning']}\n"
    #         f"Selected industry: {project['selected_industry']}\n"
    #         f"Supporting evidence: {', '.join(project['supporting_evidence'])}\n"
    #     )
    #     reasoning_lines.append("-" * 50)  # Separator
    #
    # if new_industries_reasoning:
    #     reasoning_lines.append("\nNew Industries Analysis:\n")
    #     reasoning_lines.append(new_industries_reasoning)
    #
    # reasoning_text = "\n".join(reasoning_lines)
    #
    # # Build the result dictionary
    # result = {
    #     "Industries": ", ".join(final_industries),
    #     "Reasoning about Industries": reasoning_text,
    #     "Model of_Industries_CV_extraction": model,
    #     "Completion Tokens of_Industries_CV_extraction": str(total_completion_tokens),
    #     "Prompt Tokens of_Industries_CV_extraction": str(total_prompt_tokens),
    #     "Cost_of_industries_CV_extraction": total_cost,
    #     "Cost_of_new_industries_analysis": new_analysis_cost,
    #     "Time": time.time() - start_time,
    # }
    #
    # return result
