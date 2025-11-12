

from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
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
    IndustryType = Union[Literal[*predefined_industries], str]

    class ProjectIndustryAnalysis(BaseModel):
        project_name: str = Field(description="Name or description of the project")
        supporting_evidence: List[str] = Field(description="Phrases from the resume supporting the industry choice")
        potential_industries: List[IndustryType] = Field(description="List of all potential industries from the predefined list that could fit the project")
        reasoning: str = Field(description="Reasoning for selecting the most suitable industry from potential_industries")
        selected_industry: IndustryType = Field(description="Most suitable industry selected from potential_industries")

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
                "1. List **all potential industries** from the predefined list that could fit the project.\n"
                "2. Explain your reasoning and select the **most specific and accurate industry** from the list.\n"
                "Follow these rules:\n"
                "- Always prefer the most specific industry.\n"
                "- Provide a clear explanation for your choice."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze the following project:\n\n"
                # f"**Predefined list of industries:** {industries_str}\n\n"
                f"**Project:**\n{project_text}\n\n"
                f"**Response format:**\n"
                f"- List all potential industries from the predefined list.\n"
                f"- Explain your reasoning.\n"
                f"- Select the most suitable industry."
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
    predefined_industries = list(read_specific_columns(['Industries Values'], 'values', remove_emonji=True)['Industries Values'])

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

    # Extract all unique industries
    all_industries = [project["selected_industry"] for project in projects_analysis]
    unique_industries = list(set(all_industries))

    # Separate predefined and new industries
    predefined_set = set(predefined_industries)
    new_industries = [industry for industry in unique_industries if industry not in predefined_set]
    found_industries = [industry for industry in unique_industries if industry in predefined_set]

    # Process new industries
    approved_industries, new_industries_reasoning, new_analysis_cost = process_proposed_industries(
        llm_handler=llm_handler,
        existing_industries_list=predefined_industries,
        proposed_industries=new_industries,
        model=model
    )

    # Combine all industries
    approved_industries_clean = [industry.replace("NEW ", "") for industry in approved_industries]
    final_industries = list(set(found_industries).union(set(approved_industries_clean)))

    # Build the reasoning text
    reasoning_lines = []
    for project in projects_analysis:
        reasoning_lines.append(
            f"Project: {project['project_name']}\n"
            f"Potential industries: {', '.join(project['potential_industries'])}\n"
            f"Reasoning: {project['reasoning']}\n"
            f"Selected industry: {project['selected_industry']}\n"
            f"Supporting evidence: {', '.join(project['supporting_evidence'])}\n"
        )
        reasoning_lines.append("-" * 50)  # Separator

    if new_industries_reasoning:
        reasoning_lines.append("\nNew Industries Analysis:\n")
        reasoning_lines.append(new_industries_reasoning)

    reasoning_text = "\n".join(reasoning_lines)

    # Build the result dictionary
    result = {
        "Industries": ", ".join(final_industries),
        "Reasoning about Industries": reasoning_text,
        "Model of_Industries_CV_extraction": model,
        "Completion Tokens of_Industries_CV_extraction": str(total_completion_tokens),
        "Prompt Tokens of_Industries_CV_extraction": str(total_prompt_tokens),
        "Cost_of_industries_CV_extraction": total_cost,
        "Cost_of_new_industries_analysis": new_analysis_cost,
        "Time": time.time() - start_time,
    }

    return result




# import json
# import time
# from typing import List, Literal, Type, Dict, Any
# from pydantic import BaseModel, Field, create_model
# from src.cv_parsing.info_extraction.new_industy_analysis import process_proposed_industries
# from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
# from src.data_processing.allowed_values_matcher import match_values
#
# from src.data_processing.nlp.llm_handler import LLMHandler
# from src.logger import logger  # Added logger import
#



#
# def create_industry_match_model(industries_list: List[str]) -> Type[BaseModel]:
#     """
#     Dynamically creates IndustryMatch model with Literal type for 'name' field.
#     Args:
#         industries_list: List of predefined industries for 'name' field.
#     Returns:
#         Pydantic model IndustryMatch with Literal type for 'name'.
#     """
#     if not industries_list:
#         raise ValueError("Industries list cannot be empty")
#     IndustryType = Literal[*industries_list]  # For Python < 3.11: Literal.__getitem__(tuple(industries_list))
#     return create_model(
#         'IndustryMatch',
#         supporting_projects=(List[str], Field(
#             max_length=5,
#             description="Which projects support this classification"
#         )),
#         confidence=(Literal["high", "medium", "low"], Field(
#             description="Confidence level of the match"
#         )),
#         name=(IndustryType, Field(
#             description="Exact industry name from predefined list"
#         )),
#     )
#
# class ProposedIndustry(BaseModel):
#     supporting_projects: List[str] = Field(max_length=3, description="Projects that fit this industry")
#     justification: str = Field(description="Why this industry is needed based on projects")
#     name: str = Field(description="Proposed new industry name")
#
# def create_cv_industries_extraction_model(
#     industries_list: List[str]
# ) -> Type[BaseModel]:
#     """
#     Creates CVIndustriesExtraction model with dynamic IndustryMatch and static ProposedIndustry.
#     Args:
#         industries_list: List of predefined industries.
#     Returns:
#         Pydantic model CVIndustriesExtraction.
#     """
#     IndustryMatch = create_industry_match_model(industries_list)
#     return create_model(
#         'CVIndustriesExtraction',
#         reasoning_steps=(List[str], Field(
#             description="Step-by-step analysis in bullet points"
#         )),
#         matched_industries=(List[IndustryMatch], Field(
#             default_factory=list,
#             max_length=15,
#             description="Industries matched from predefined list"
#         )),
#         proposed_industries=(List[ProposedIndustry], Field(
#             default_factory=list,
#             max_length=8,
#             description="New industries not in predefined list"
#         )),
#     )
#
#
# def extract_cv_industries(
#         cv_sections: Dict,
#         llm_handler: LLMHandler,
#         model: str = "gpt-4.1-nano"
# ):
#     """
#     Extract CV industries using SGR approach with dynamic industries list.
#     """
#     start_time = time.time()
#     # Load existing industries dynamically from Google Sheets
#     industries_list = list(read_specific_columns(['Industries Values'], 'values', remove_emonji=True)['Industries Values'])
#     industries_str = '", "'.join(industries_list)
#     industries_formatted = f'"{industries_str}"'
#
#     cv = get_section_for_field(cv_sections, "Industries")
#     prompt = [
#         {
#             "role": "system",
#             "content": "You are an expert industries analyst specializing in data categorization."
#         },
#         {
#             "role": "user",
#             "content": (
#                 f"Analyze projects in this resume and classify them against existing industries.\n\n"
#                 f"**Predefined list of accepted industries:** {industries_formatted}\n\n"
#                 f"**Classification Rules:**\n"
#                 f"1. Read through all project descriptions to understand their core function and domain\n"
#                 f"2. For each project, identify potential industries\n"
#                 f"3. Compare identified industries against the predefined list\n"
#                 f"4. Match to existing industries when possible\n"
#                 f"5. Propose new industries only when no good match exists\n"
#                 f"6. Provide confidence levels and supporting evidence\n\n"
#                 f"**Resume:**\n{cv}"
#             )
#         }
#     ]
#     max_tokens = max(len(cv)*2, 800)
#     # Create CVIndustriesExtraction model dynamically
#     CVIndustriesExtraction = create_cv_industries_extraction_model(industries_list)
#     # Use structured output
#     response = llm_handler.get_answer(
#         prompt,
#         model=model,
#         max_tokens=max_tokens,
#         response_format=CVIndustriesExtraction
#     )
#
#     # Process structured response
#     industries_extraction = response['parsed']
#     usage = response['usage']
#     cost_info = response['cost']
#
#     def extract_industry_names(industry_objects: List[Any]) -> List[str]:
#         return [industry.name for industry in industry_objects]
#
#     # Validate matched industries against actual list (important validation!)
#     matched_industry_names = extract_industry_names(industries_extraction.matched_industries)
#     validated_matches, additional_proposed = match_values(industries_list, matched_industry_names)
#     if len(additional_proposed):
#             print("len of additional_proposed industries: ", additional_proposed)
#
#     # Combine all proposed industries
#     proposed_industry_names = extract_industry_names(industries_extraction.proposed_industries)
#     matches_industries_set, proposed_industries_set = match_values(industries_list, proposed_industry_names)
#     all_proposed_unique = list(proposed_industries_set.union(additional_proposed))  # Remove duplicates
#
#     # Process new industries individually
#     approved_industries, total_new_analysis_cost = process_proposed_industries(
#         llm_handler=llm_handler,
#         existing_industries_list=industries_list,
#         proposed_industries=all_proposed_unique,
#         model=model
#     )
#
#     # Final result
#     final_industries = list(validated_matches.union(set(approved_industries)))
#
#     # Build result dictionary with all fields
#     result = {
#         "Industries": ', '.join(final_industries),
#         "Reasoning about Industries": "\n".join(f"• {step}" for step in industries_extraction.reasoning_steps),
#         "Model of_Industries_CV_extraction": model,
#         "Completion Tokens of_Industries_CV_extraction": str(usage.completion_tokens),
#         "Prompt Tokens of_Industries_CV_extraction": str(usage.prompt_tokens),
#         "Cost_of_industries_CV_extraction": cost_info['total_cost'],
#         "Cost_of_new_industries_analysis": total_new_analysis_cost,
#             "Time" : time.time()-start_time,
#     }
#
#     # Log the complete response in a single entry
#     logger.info(f"Field extraction completed - Field: 'Industries' | Response: {json.dumps(result, ensure_ascii=False)}")
#
#     return result
