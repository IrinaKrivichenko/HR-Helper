import json

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class Project(BaseModel):
    name: str = Field(description="Project name (exact from resume)")
    description: str = Field(description="Project description (exact from resume)")
    activities: Optional[List[str]] = Field(description="List of responsibilities and activities (exact from resume)", default=None)
    achievements: Optional[List[str]] = Field(description="List of achievements (exact from resume)", default=None)

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
                "1. Project name (exact from resume).\n"
                "2. Project description (exact from resume).\n"
                "3. List of responsibilities and activities (exact from resume).\n"
                "4. List of achievements (exact from resume).\n"
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
    lines = [
        f"Project: {project['name']}",
        f"Description: {project['description']}"
    ]
    if project.get("activities"):
        lines.append(f"Activities: {', '.join(project['activities'])}")
    if project.get("achievements"):
        lines.append(f"Achievements: {', '.join(project['achievements'])}")
    return "\n".join(lines)

def extract_cv_projects_achievements(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts achievements for each project in parallel.
    Returns combined text, tokens, and cost.
    """
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
            total_cost += result["cost"]

    combined_text = "\n\n".join(format_project(project) for project in projects)

    return {
        "combined_text": combined_text,
        "completion_tokens": total_completion_tokens,
        "prompt_tokens": total_prompt_tokens,
        "cost": total_cost,
    }

