from typing import List, Any, Dict
from pydantic import BaseModel, Field

from src.data_processing.jaccard_similarity import find_similar_lines


class ProjectsStarts(BaseModel):
    project_count: int = Field(description="Number of projects in the text.")
    reasoning: str = Field(description="Brief explanation of how the project starts were identified.")
    project_starts: List[str] = Field(description="List of strings that indicate the start of each project in the text.")

def get_project_starts(llm_handler: Any, model: str, experience_text: str) -> Dict[str, Any]:
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in parsing resumes and extracting structured information. "
                "Your task is to analyze the provided 'experience' section of a resume and identify the start of each project."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze the following 'experience' section of a resume:\n\n{experience_text}\n\n"
                "1. Determine the number of projects in the text.\n"
                "2. Provide a brief explanation of how you identified the start of each project.\n"
                "3. List the strings that indicate the start of each project.\n\n"
                "A project start is typically a line that introduces a new project, "
                # "such as a project name, a role in a project, or an explicit marker like 'PROJECTS'.\n\n"
                # "Respond in JSON format according to the `ProjectsStarts` model."
            )
        }
    ]
    response = llm_handler.get_answer(
        prompt,
        model=model,
        response_format=ProjectsStarts,
        max_tokens=2000
    )
    usage = response['usage']
    cost_info = response['cost']
    result = {
        "projects_starts": response["parsed"],
        "usage": usage,
        "cost": cost_info
    }
    return result

def extract_projects(experience_text: str, project_starts: List[str]) -> List[str]:
    """
    Extract projects from the experience section using the provided list of project start strings.
    Args:
        experience_text: Text of the experience section.
        project_starts: List of strings that indicate the start of each project.
    Returns:
        List[str]: List of project text blocks in the order of their first appearance.
    """
    lines = experience_text.split('\n')
    index_to_start: Dict[int, str] = {}
    start_to_text: Dict[str, str] = {}

    # Find all indices of lines that could be the start of a project
    for start in project_starts:
        similar_lines = find_similar_lines(lines, start)
        for index, similarity in similar_lines:
            index_to_start[index] = start

    # Sort indices to process lines in order of appearance
    sorted_indices = sorted(index_to_start.keys())
    first_start_index = sorted_indices[0]
    # Extract information before the first project start
    pre_project_lines = lines[:first_start_index]
    pre_project_text = '\n'.join(pre_project_lines).strip()

    # Extract projects
    for i in range(len(sorted_indices)):
        start_index = sorted_indices[i]
        start = index_to_start[start_index]
        end_index = sorted_indices[i+1] if i+1 < len(sorted_indices) else len(lines)

        project_lines = lines[start_index:end_index]
        project_text = '\n'.join(project_lines).strip()

        if start in start_to_text:
            start_to_text[start] += "\n" + project_text
        else:
            start_to_text[start] = project_text

    # Return projects in the order of their first appearance
    ordered_projects = []
    for start in project_starts:
        if start in start_to_text:
            ordered_projects.append(start_to_text[start])

    # Add pre-project information as the first project if it's larger than the smallest project
    if pre_project_text and ordered_projects:
        smallest_project_size = min(len(project) for project in ordered_projects)
        if len(pre_project_text) > smallest_project_size:
            ordered_projects.insert(0, pre_project_text)

    return ordered_projects

def iterative_project_extraction(llm_handler: Any, model: str, experience_text: str) -> Dict[str, Any]:
    total_prompt_tokens = 0
    total_cost = 0.0
    path_steps = []
    all_project_starts = []
    projects_text = experience_text
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        project_starts_result = get_project_starts(llm_handler, model, projects_text)
        project_starts_info = project_starts_result["projects_starts"]
        project_count = project_starts_info.project_count
        project_starts = project_starts_info.project_starts
        reasoning = project_starts_info.reasoning

        total_prompt_tokens += project_starts_result["usage"].prompt_tokens + project_starts_result["usage"].completion_tokens
        total_cost += project_starts_result["cost"]["total_cost"]

        path_steps.append(f"Project extraction iteration: Found {project_count} projects. Reasoning: {reasoning}")

        # Add new project starts to the overall list
        lines = experience_text.split('\n')
        # Find similar lines for each project start
        for start in project_starts:
            similar_lines = find_similar_lines(lines, start)
            for index, similarity in similar_lines:
                line = lines[index]
                if line not in all_project_starts:
                    all_project_starts.append(line)
        # Extract projects using all project starts found so far
        projects = extract_projects(experience_text, all_project_starts)
        unique_project_starts = list(set(project_starts))
        if len(unique_project_starts) <= 3 and project_count == len(project_starts):
            path_steps.append(f"Last iteration {iteration}: {project_count} projects extracted.")
            break
        else:
            # Select the three largest projects
            projects_sorted = sorted(projects, key=len, reverse=True)[:3]
            projects_text = "\n\n".join(projects_sorted)
            path_steps.append(f"Iteration {iteration}: Selected top 3 largest projects for re-evaluation.")

    return {
        "projects": projects,
        "project_starts": project_starts,
        "project_count": project_count,
        "path_steps": path_steps,
        "total_prompt_tokens": total_prompt_tokens,
        "total_cost": total_cost
    }
