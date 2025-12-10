import json

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field, conint
from typing import List, Dict, Optional, Any

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import

YearType = conint(ge=1900, le=2100) # year from 1900 to 2100
MonthType = conint(ge=1, le=12)     # month from 1 to 12

class Project(BaseModel):
    company_name: Optional[str] = Field(default=None,  description="Company name (must be exactly as in CV)")
    project_name: Optional[str] = Field(default=None, description="Project name (must be exactly as in CV)")
    project_company_name: Optional[str] = Field(default=None, description="Project client or company name (must be exactly as in CV)")
    project_locations: Optional[List[str]] = Field(default=None, description="Project locations (must be exactly as in CV)")
    project_start_year: Optional[YearType] = Field( default=None, description="Project start year (must be exactly as in CV, between 1900 and 2100)")
    project_start_month: Optional[MonthType] = Field(default=None, description="Project start month as a number (1-12), if specified in CV")
    project_end_year: Optional[YearType] = Field(default=None, description="Project end year (must be exactly as in CV, between 1900 and 2100)")
    project_end_month: Optional[MonthType] = Field(default=None, description="Project end month as a number (1-12), if specified in CV")
    project_roles: Optional[List[str]] = Field(default=None, description="Roles in the project (must be exactly as in CV)")
    project_stack: Optional[List[str]] = Field(default=None, description="Technology stack used in the project (must be exactly as in CV)")
    project_description: Optional[str] = Field(default=None, description="Project description (must be exactly as in CV)")
    project_activities: Optional[List[str]] = Field(default=None, description="List of responsibilities and activities (must be exactly as in CV)")
    project_achievements: Optional[List[str]] = Field(default=None, description="List of achievements (must be exactly as in CV)")
    links_connected_to_the_project: Optional[List[str]] = Field(default=None, description="Links related to the project (must be exactly as in CV)")

def extract_achievements_for_project(
    project_text: str,
    llm_handler: LLMHandler,
    model: str
) -> Dict[str, Any]:
    """
    Extracts project name, description, and achievements from a single project text.
    Returns structured data with tokens and cost.
    """
    prompt = [
        {
            "role": "system",
            "content": (
                "Extract the following details from the project text:\n"
                "1. Company name (must be exactly as in CV).\n"
                "2. Project name (must be exactly as in CV).\n"
                "3. Project client or company name (must be exactly as in CV).\n"
                "4. Project locations (must be exactly as in CV).\n"
                "5. Project start year (must be exactly as in CV, between 1900 and 2100).\n"
                "6. Project start month as a number (1-12), if specified in CV.\n"
                "7. Project end year (must be exactly as in CV, between 1900 and 2100).\n"
                "8. Project end month as a number (1-12), if specified in CV.\n"
                "9. Roles in the project (must be exactly as in CV).\n"
                "10. Technology stack used in the project (must be exactly as in CV).\n"
                "11. Project description (must be exactly as in CV).\n"
                "12. List of responsibilities and activities (must be exactly as in CV).\n"
                "13. List of achievements (must be exactly as in CV).\n"
                "14. Links related to the project (must be exactly as in CV)"
            )
        },
        {
            "role": "user",
            "content": f"Project text:\n{project_text}"
        }
    ]

    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        response_format=Project  # Pydantic model for structured output
    )

    # Extract parsed data, usage, and cost
    project_data = response["parsed"].model_dump()
    usage = response["usage"]
    cost = response["cost"]["total_cost"]

    return {
        "project": project_data,
        "completion_tokens": usage.completion_tokens,
        "prompt_tokens": usage.prompt_tokens,
        "cost": cost,
    }


def format_project(project: Dict[str, Any]) -> str:
    """Formats projects into a human-readable string, including all fields."""
    def fmt(y: Optional[int], m: Optional[int]) -> str:
        if y and m:
            return f"{y}-{m:02d}"
        if y:
            return str(y)
        return ""

    formatted = []
    project_info = []
    if project.get('project_name', '') and project.get('project_name')!="None":
        project_info.append(f"Project: {project.get('project_name')}")
    if project.get('company_name', '') and project.get('company_name')!="None":
        project_info.append(f"Company: {project.get('company_name', '')}")
    if project.get('project_company_name', '') and project.get('project_company_name')!="None":
        project_info.append(f"Client/Company: {project.get('project_company_name', '')}")
    if project.get('project_locations', ''):
        project_info.append(f"Locations: {', '.join(project.get('project_locations', ''))}")
    # Format dates
    start_year, start_month = project.get('project_start_year', 0), project.get('project_start_month', 0)
    end_year, end_month = project.get('project_end_year', 0), project.get('project_end_month', 0)
    if start_year or start_month or end_year or end_month:
        period = f"{fmt(start_year, start_month)} — {fmt(end_year, end_month) or 'present'}"
        project_info.append(f"Period: {period.strip()}")
    if project.get('project_roles', ''):
        project_info.append(f"Roles: {', '.join(project.get('project_roles', ''))}")
    if project.get('project_stack', ''):
        project_info.append(f"Stack: {', '.join(project.get('project_stack', ''))}")
    if project.get('project_description', ''):
        project_info.append(f"Description: {project.get('project_description', '')}")
    if project.get('project_activities', ''):
        project_info.append(f"Activities: {'; '.join(project.get('project_activities', ''))}")
    if project.get('project_achievements', ''):
        project_info.append(f"Achievements: {'; '.join(project.get('project_achievements', ''))}")
    if project.get('links_connected_to_the_project', ''):
        project_info.append(f"Links: {'; '.join(project.get('links_connected_to_the_project', ''))}")

    formatted.append("\n".join(project_info))
    return "\n\n".join(formatted)


def extract_cv_expertise(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts achievements for each project in parallel.
    Returns combined text, tokens, and cost.
    """
    start_time = time.time()
    projects_list = get_section_for_field(cv_sections, "Projects")

    projects = []
    total_completion_tokens = 0
    total_prompt_tokens = 0
    total_cost = 0.0

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                extract_achievements_for_project,
                project_text,
                llm_handler,
                model
            )
            for project_text in projects_list
        ]

        for future in as_completed(futures):
            result = future.result()
            projects.append(result["project"])
            total_completion_tokens += result["completion_tokens"]
            total_prompt_tokens += result["prompt_tokens"]
            total_prompt_tokens += result["prompt_tokens"]
            total_cost += result["cost"]

    combined_text = "\n\n".join(format_project(project) for project in projects)

    result = {
            "Expertise": combined_text,
            "Reasoning about Expertise": "",
            "Model of_Expertise_CV_extraction": model,
            "Completion Tokens of_Expertise_CV_extraction": str(total_completion_tokens),
            "Prompt Tokens _of_Expertise_CV_extraction": str(total_prompt_tokens),
            "Cost_of_Expertise_CV_extraction": total_cost,
            "Time" : time.time()-start_time
        }
    logger.info(f"Field extraction completed - Field: 'Expertise' | Response: {json.dumps(result, ensure_ascii=False)}")
    return result


