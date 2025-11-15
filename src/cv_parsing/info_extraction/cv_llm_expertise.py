import json

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from src.cv_parsing.info_extraction.cv_llm_expertise_achievements import extract_cv_projects_achievements
from src.cv_parsing.info_extraction.cv_llm_expertise_certificates import extract_cv_certificates
from src.data_processing.nlp.llm_handler import LLMHandler


def extract_cv_expertise(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts expertise (projects achievements and certificates) from a resume in parallel.
    Returns combined expertise text with tokens and cost.
    """
    start_time = time.time()

    with ThreadPoolExecutor() as executor:
        achievements_future = executor.submit(
            extract_cv_projects_achievements,
            cv_sections,
            llm_handler,
            model
        )
        certificates_future = executor.submit(
            extract_cv_certificates,
            cv_sections,
            llm_handler,
            model
        )

        projects_achievements = achievements_future.result()
        certificates = certificates_future.result()

    # Combine all expertise into a single text field
    expertise_parts = []
    # Add projects achievements
    expertise_parts.append(f"Projects:\n{projects_achievements['combined_text']}")
    # Add certificates only if they exist
    certificates_text = certificates['combined_text'].strip()
    if certificates_text:
        expertise_parts.append(f"Certificates:\n{certificates_text}")
    # Join all parts with double newlines
    expertise_text = "\n\n".join(expertise_parts)

    result = {
        "Expertise": expertise_text,
        "Model of_Expertise_CV_extraction": model,
        "Completion Tokens of_Expertise_CV_extraction": str(
            projects_achievements["completion_tokens"] + certificates["completion_tokens"]
        ),
        "Prompt Tokens of_Expertise_CV_extraction": str(
            projects_achievements["prompt_tokens"] + certificates["prompt_tokens"]
        ),
        "Cost_of_Expertise_CV_extraction": (
            projects_achievements["cost"] + certificates["cost"]
        ),
        "Time": time.time() - start_time,
    }

    return result



# class ExpertiseArea(BaseModel):
#     category: str = Field(description="Expertise category (e.g., 'Leadership & Management', 'Data & Analytics')")
#     description: str = Field(description="Detailed description of expertise in this area")
#
#
# class CVExpertiseAnalysis(BaseModel):
#     reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
#     expertise_areas: List[ExpertiseArea] = Field(description="List of expertise areas with descriptions")
#
#
# def extract_cv_expertise(
#         cv_sections: Dict,
#     llm_handler: LLMHandler,
#     model: str = "gpt-5-nano"
# ):
#     """
#     Extract CV expertise using structured outputs.
#     """
#     start_time = time.time()
#     cv = get_section_for_field(cv_sections, "Expertise")
#     prompt = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a hybrid AI assistant embodying three expert personas: "
#                 "Senior Sales Executive, Principal AI Engineer, and Veteran Technical Recruiter."
#             )
#         },
#         { ## куски резюме
#             "role": "user",
#             "content": (
#                 f"Analyze this resume and extract the candidate's core 'Expertise'.\n\n"
#                 f"**Definition of 'Expertise':** Summary of HOW skills were applied to solve business problems "
#                 f"and deliver results. Focus on processes, achievements, methodologies, and business outcomes.\n\n" ##percentage and numbers
#                 f"**Process:**\n"
#                 f"1. Scan for certifications and their links\n"
#                 f"2. Identify key achievements and responsibilities\n"
#                 f"3. Abstract from specific tools to general capabilities\n"
#                 f"4. Group related concepts and link to certifications\n\n"
#                 f"**Categories to consider:**\n"
#                 f"- Leadership & Management\n"
#                 f"- Data & Analytics\n"
#                 f"- Architecture & Performance\n"
#                 f"- Development & Engineering\n"
#                 f"- Business & Strategy\n"
#                 f"- Other relevant areas\n\n"
#                 f"**Resume:**\n{cv}"
#             )
#         }
#     ]
#
#     # Calculate max tokens based on CV length
#     max_tokens = max(len(cv)*3, 800)
#
#     # Use structured output
#     response = llm_handler.get_answer(
#         prompt,
#         model=model,
#         max_tokens=max_tokens,
#         response_format=CVExpertiseAnalysis
#     )
#
#     # Process structured response
#     expertise_analysis = response['parsed']
#     usage = response['usage']
#     cost_info = response['cost']
#
#     # Get cached tokens if available
#     cached_tokens = 0
#     if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
#         cached_tokens = usage.prompt_tokens_details.cached_tokens
#
#     # Format expertise areas into the original string format
#     expertise_string = ""
#     if expertise_analysis.expertise_areas:
#         expertise_lines = []
#         for area in expertise_analysis.expertise_areas:
#             expertise_lines.append(f"{area.category} | {area.description}")
#         expertise_string = "\n".join(expertise_lines)
#
#     # Build result dictionary with all fields
#     result = {
#         "Expertise": expertise_string,
#         "Reasoning about Expertise": "\n".join(f"• {step}" for step in expertise_analysis.reasoning_steps),
#         "Model of_Expertise_CV_extraction": model,
#         "Completion Tokens of_Expertise_CV_extraction": str(usage.completion_tokens),
#         "Prompt Tokens _of_Expertise_CV_extraction": str(usage.prompt_tokens),
#         "Cached Tokens of_Expertise_CV_extraction": str(cached_tokens),
#         "Cost_of_Expertise_CV_extraction": cost_info['total_cost'],
#             "Time" : time.time()-start_time
#     }
#
#     # Log the complete response in a single entry
#     logger.info(f"Field extraction completed - Field: 'Expertise' | Response: {json.dumps(result, ensure_ascii=False)}")
#
#     return result
