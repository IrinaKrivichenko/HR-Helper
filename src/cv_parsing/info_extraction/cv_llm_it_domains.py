

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from annotated_types import MinLen, MaxLen
from typing_extensions import Annotated

def create_project_it_domains_model(predefined_it_domains: List[str]) -> type[BaseModel]:
    """
    Creates a Pydantic model for analyzing IT domains of a project.
    Args:
        predefined_it_domains: List of predefined IT domains.
    Returns:
        A Pydantic model class for IT domains analysis.
    """
    # Create a Literal type for predefined IT domains
    ITDomainLiteral = Literal[*predefined_it_domains]

    # Define the ITDomainAnalysis model
    class ITDomainAnalysis(BaseModel):
        supporting_evidence: Annotated[List[str], MaxLen(5)] = Field(default=[], description="Phrases from the resume supporting the IT domain choice.")
        reasoning: Optional[str] = Field(default=None, description="Reasoning for selecting the IT domain.")
        selected_it_domain: Optional[ITDomainLiteral] = Field(default=None, description="Selected IT domain from the predefined list.")
        new_it_domain: Optional[str] = Field(default=None, description="New IT domain if none from the predefined list fits.")
        confidence: float = Field(ge=0, le=1, description="Confidence level (0 to 1) in the IT domain selection.")

    # Define the main ProjectITDomainsAnalysis model
    class ProjectITDomainsAnalysis(BaseModel):
        project_name: str = Field(description="Name or description of the project.")
        reasoning: str = Field(description="Overall reasoning for IT domain selection. Please be brief.")
        has_enough_info: bool = Field(description="Whether there is enough information to determine IT domains.")
        it_domains: Annotated[List[ITDomainAnalysis], MinLen(5), MaxLen(15)] = Field(description="List of IT domain analyses for the project.")

    return ProjectITDomainsAnalysis

def generate_it_domains_prompt(project_text: str, predefined_it_domains: List[str]) -> List[Dict[str, str]]:
    """
    Generates a prompt for analyzing IT domains of a project.
    Args:
        project_text: Text of the project to analyze.
        predefined_it_domains: List of predefined IT domains.
    Returns:
        A list of dictionaries representing the prompt messages.
    """
    # Format predefined IT domains as a string
    it_domains_str = ", ".join(f'"{domain}"' for domain in predefined_it_domains)
    # Define the prompt
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in analyzing resumes and determining IT domains of projects. "
                "Your task is to analyze the project and determine which IT domains it belongs to.\n"
                "Follow these rules:\n"
                "1. Analyze the project for IT domains from the predefined list.\n"
                "2. Select all suitable IT domains from the list. A project can belong to multiple IT domains.\n"
                "3. If no suitable IT domain is found, suggest a new IT domain.\n"
                "4. Specify a confidence level (0 to 1) for each selected IT domain.\n"
                "5. Justify the selection of each IT domain using phrases from the project text (`supporting_evidence`).\n"
                "6. If there is not enough information, set `has_enough_info` to `False`."
            )
        },
        {
            "role": "user",
            "content": (
                "Analyze the following project and determine its IT domains:\n\n"
                f"**Predefined IT domains:** {it_domains_str}\n\n"
                "Response requirements:\n"
                "1. Specify the project name (`project_name`).\n"
                "2. List phrases from the text supporting the IT domain selection (`supporting_evidence`).\n"
                "3. Justify the selection of each IT domain (`reasoning`).\n"
                "4. Indicate whether there is enough information to determine IT domains (`has_enough_info`).\n"
                "5. For each IT domain, specify:\n"
                "   - `selected_it_domain` (if the IT domain is from the predefined list),\n"
                "   - `new_it_domain` (if the IT domain is new),\n"
                "   - `confidence` (confidence level from 0 to 1).\n\n"
                f"**Project text:**\n{project_text}"
            )
        }
    ]
    return prompt

def format_it_domains_reasoning(project_analysis: Dict[str, Any]) -> str:
    """
    Formats the IT domains analysis of a project into a readable text.
    Args:
        project_analysis: Dictionary with the project's IT domains analysis.
    Returns:
        Formatted string with the reasoning for IT domain selection.
    """
    # Start with project name and info sufficiency
    lines = [
        f"Project: {project_analysis['project_name']}",
        f"Enough information: {'Yes' if project_analysis['has_enough_info'] else 'No'}"
    ]
    # If not enough information, return early
    if not project_analysis['has_enough_info']:
        return "\n".join(lines)
    # Add overall reasoning
    lines.append(f"Reasoning: {project_analysis['reasoning']}")
    lines.append("\nIT Domains:")
    # Add details for each IT domain
    for domain in project_analysis['it_domains']:
        domain_name = domain.get('selected_it_domain') or domain.get('new_it_domain')
        lines.append(
            f"- {domain_name} (confidence: {domain['confidence']:.2f})\n"
            f"  Reasoning: {domain['reasoning']}\n"
            f"  Supporting evidence: {', '.join(domain['supporting_evidence'])}\n"
        )
    return "\n".join(lines)


def analyze_single_project_it_domains(
    project_text: str,
    predefined_it_domains: List[str],
    llm_handler: Any,  # Replace with your LLM handler type
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Analyzes IT domains for a single project and returns the analysis result.

    Args:
        project_text: Text of the project to analyze.
        predefined_it_domains: List of predefined IT domains.
        llm_handler: Handler for interacting with the LLM.
        model: Name of the model to use for analysis.

    Returns:
        Dictionary with the project's IT domains analysis.
    """
    # Create Pydantic model for IT domains
    ProjectITDomainsModel = create_project_it_domains_model(predefined_it_domains)
    # Generate prompt
    prompt = generate_it_domains_prompt(project_text, predefined_it_domains)
    # Get response from LLM
    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=3021,
        response_format=ProjectITDomainsModel,
    )
    # Format the result
    project_analysis = response["parsed"].model_dump()
    project_analysis["usage"] = response["usage"]
    project_analysis["cost"] = response["cost"]
    return project_analysis

