import concurrent.futures
from typing import Dict, Any

from src.cv_parsing.sections.projects_extraction import extract_projects_iteratively
from src.cv_parsing.sections.section_identifier import identify_resume_sections


def identify_resume_sections_and_projects(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Parallelly extracts structured resume sections and projects.
    Returns a unified dictionary with results from both functions.
    """
    def run_identify_sections():
        return identify_resume_sections(cv_text, llm_handler, model)

    def run_extract_projects():
        return extract_projects_iteratively(cv_text, llm_handler, model)

    # Run both functions in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        sections_future = executor.submit(run_identify_sections)
        projects_future = executor.submit(run_extract_projects)

        sections_result = sections_future.result()
        projects_result = projects_future.result()

    # Merge results
    unified_result = {
        **sections_result,
        **projects_result,
    }

    return unified_result
