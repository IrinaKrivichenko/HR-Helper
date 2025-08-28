# from src.nlp.llm_handler import LLMHandler, extract_and_parse_token_section
#
# def parse_llm_cv_expertise_response(llm_response: str, add_tokens_info: bool = False) -> dict:
#     """
#     Parses the LLM response for a CV expertise analysis.
#     Extracts reasoning (if add_tokens_info=True), expertise summary, and cost information.
#     Args:
#         llm_response (str): Model's response with "Reasoning:" and "Final Answer:" sections.
#         add_tokens_info (bool): If True, includes reasoning and uses "Cost" as the cost key.
#     Returns:
#         dict: Dictionary with keys:
#             - "Reasoning about Expertise": Detailed reasoning (only if add_tokens_info=True).
#             - "Expertise": Structured expertise summary (empty string if none).
#             - "Cost" or "Cost_of_Expertise_CV_extraction": Cost of the API call (always included).
#             - All keys from tokens_data (only if add_tokens_info=True).
#     """
#     # Extract and clean the response (remove token section)
#     cleaned_response, token_data = extract_and_parse_token_section(
#         response=llm_response,
#         additional_key_text="",
#         add_tokens_info=add_tokens_info
#     )
#
#     result = {"Expertise": ""}
#
#     # Extract reasoning if add_tokens_info=True
#     if add_tokens_info:
#         lines = cleaned_response.strip().split('\n')
#         reasoning_lines = []
#         for line in lines:
#             if line.startswith("Final Answer:"):
#                 break
#             reasoning_lines.append(line)
#         result["Reasoning about Expertise"] = "\n".join(reasoning_lines).strip()
#
#     cleaned_response = cleaned_response.replace("**Expertise:**", "")
#     # Extract expertise from "Final Answer:" section
#     final_answer_section = False
#     expertise_lines = []
#     for line in cleaned_response.strip().split('\n'):
#         if line.startswith("Final Answer:"):
#             final_answer_section = True
#             continue
#         if final_answer_section and line.strip():
#             expertise_lines.append(line.strip())
#
#     if expertise_lines:
#         result["Expertise"] = "\n".join(expertise_lines)
#
#     # Extract cost from token_data (always included)
#     if "Cost" in token_data:
#         cost = float(token_data["Cost"].replace("$", ""))
#         if add_tokens_info:
#             result["Cost"] = cost  # Benchmark mode: simple "Cost" key
#         else:
#             result["Cost_of_Expertise_CV_extraction"] = cost  # Working mode: detailed key
#
#     # Append full tokens_data only if add_tokens_info=True
#     if add_tokens_info:
#         result.update(token_data)
#
#     return result
#
#
# def extract_cv_expertise(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a hybrid AI assistant embodying three expert personas: "
#                 "1. A **Senior Sales Executive** who understands client needs and business value. "
#                 "2. A **Principal AI Engineer** who deeply understands technical processes and capabilities. "
#                 "3. A **Veteran Technical Recruiter** with 10 years of experience in identifying talent and achievements. "
#                 "Your goal is to synthesize a candidate's resume into a high-level summary of their expertise. "
#                 "**First, explain your reasoning step-by-step in bullet points.** "
#                 "Then, return the final output in the required format."
#             )
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Analyze the following resume and extract the candidate's core 'Expertise'. "
#                 "**Explain your reasoning step-by-step**, then return the final output in the required format.\n\n"
#                 "**Crucial Definition of 'Expertise':** "
#                 "'Expertise' is NOT a list of technologies, roles, industries, or languages. "
#                 "It is the summary of **HOW** those skills were applied to solve business problems and deliver results. "
#                 "Focus on processes, achievements, methodologies, and business outcomes.\n\n"
#                 "**Your internal thought process must be:**\n"
#                 "1. **Scan for Certifications:** Identify all certifications and their links.\n"
#                 "2. **Identify Achievements:** Extract key achievements and responsibilities from project descriptions.\n"
#                 "3. **Abstract Competence:** Move from specific tools to general capabilities.\n"
#                 "4. **Synthesize and Link:** Group related concepts and link to certifications where applicable.\n\n"
#                 "**Output Instructions:**\n"
#                 "1. **Reasoning:** [Your step-by-step analysis in bullet points].\n"
#                 "2. **Final Answer:** [Structured expertise summary].\n\n"
#                 "**Format Example:**\n"
#                 "Reasoning:\n"
#                 "- Found certification 'Databricks Certified Data Engineer Professional' → Will link to Data & Analytics expertise.\n"
#                 "- Project describes building scalable systems → Will add to Architecture & Performance.\n"
#                 "Final Answer:\n"
#                 "Leadership & Management | Oversaw development teams; experienced in team building and strategic planning.\n"
#                 "Data & Analytics | Developed predictive models (validated by Databricks Certified Data Engineer Professional: https://example.com/cert/123); data visualization; forecast sales.\n"
#                 "Architecture & Performance | Built scalable, high-performance systems; optimized database performance.\n\n"
#                 "**Here is the CV:**\n"
#                 f"{cv}"
#             )
#         }
#     ]
#
#     # Calculate max tokens based on the length of the vacancy description
#     max_tokens = max(len(cv), 200)
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#     print(response)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_cv_expertise_response(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data

from pydantic import BaseModel, Field
from typing import List, Optional

from src.nlp.llm_handler import LLMHandler, extract_and_parse_token_section


class ExpertiseArea(BaseModel):
    category: str = Field(description="Expertise category (e.g., 'Leadership & Management', 'Data & Analytics')")
    description: str = Field(description="Detailed description of expertise in this area")

class CVExpertiseAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    expertise_areas: List[ExpertiseArea] = Field(description="List of expertise areas with descriptions")


def extract_cv_expertise(cv: str, llm_handler: LLMHandler, model="gpt-5-nano", add_tokens_info: bool = False):
    """
    Extract CV expertise using structured outputs.
    """

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a hybrid AI assistant embodying three expert personas: "
                "Senior Sales Executive, Principal AI Engineer, and Veteran Technical Recruiter."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume and extract the candidate's core 'Expertise'.\n\n"
                f"**Definition of 'Expertise':** Summary of HOW skills were applied to solve business problems "
                f"and deliver results. Focus on processes, achievements, methodologies, and business outcomes.\n\n"
                f"**Process:**\n"
                f"1. Scan for certifications and their links\n"
                f"2. Identify key achievements and responsibilities\n"
                f"3. Abstract from specific tools to general capabilities\n"
                f"4. Group related concepts and link to certifications\n\n"
                f"**Categories to consider:**\n"
                f"- Leadership & Management\n"
                f"- Data & Analytics\n"
                f"- Architecture & Performance\n"
                f"- Development & Engineering\n"
                f"- Business & Strategy\n"
                f"- Other relevant areas\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    # Calculate max tokens based on CV length
    max_tokens = max(len(cv), 200)

    # Use structured output
    response = llm_handler.get_answer(
        prompt, model=model, max_tokens=max_tokens,
        response_format=CVExpertiseAnalysis
    )

    # Process structured response (assuming it always exists)
    expertise_analysis = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Build result dictionary in the original format
    result = {"Expertise": ""}

    if add_tokens_info:
        result["Reasoning about Expertise"] = "\n".join([f"• {step}" for step in expertise_analysis.reasoning_steps])
        result["Model Used"] = model
        result["Completion Tokens"] = str(usage.completion_tokens)
        result["Prompt Tokens"] = str(usage.prompt_tokens)
        cached_tokens = usage.prompt_tokens_details.cached_tokens if hasattr(usage, 'prompt_tokens_details') else 0
        result["Cached Tokens"] = str(cached_tokens)
        result["Cost"] = f"${cost_info['total_cost']:.6f}"

    # Format expertise areas into the original string format
    if expertise_analysis.expertise_areas:
        expertise_lines = []
        for area in expertise_analysis.expertise_areas:
            expertise_lines.append(f"{area.category} | {area.description}")
        result["Expertise"] = "\n".join(expertise_lines)

    # Add cost info
    if not add_tokens_info:
        result["Cost_of_Expertise_CV_extraction"] = cost_info['total_cost']

    return result
#
# def _fallback_cv_expertise_parse(response: str, token_data: dict, add_tokens_info: bool) -> dict:
#     """
#     Fallback parser for CV expertise extraction when structured output fails.
#     """
#     result = {"Expertise": ""}
#
#     if add_tokens_info:
#         result["Reasoning about Expertise"] = "Unable to extract reasoning from response"
#         result["Model Used"] = "unknown"
#         result["Completion Tokens"] = "0"
#         result["Prompt Tokens"] = "0"
#         result["Cached Tokens"] = "0"
#         result["Cost"] = "$0.000000"
#
#     # Try to extract expertise from response text (basic fallback)
#     # Look for "Final Answer:" section or any structured content
#     lines = response.strip().split('\n') if response else []
#     final_answer_section = False
#     expertise_lines = []
#
#     for line in lines:
#         if line.startswith("Final Answer:"):
#             final_answer_section = True
#             continue
#         if final_answer_section and line.strip() and not line.startswith("##"):
#             expertise_lines.append(line.strip())
#
#     if expertise_lines:
#         result["Expertise"] = "\n".join(expertise_lines)
#
#     # Add cost info
#     if not add_tokens_info:
#         result["Cost_of_Expertise_CV_extraction"] = 0.0
#
#     return result

