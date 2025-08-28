# from src.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler, extract_and_parse_token_section
#
# def parse_llm_cv_stack_response(llm_response: str, add_tokens_info: bool = False) -> dict:
#     """
#     Parses the LLM response for a CV technology stack analysis.
#     Extracts reasoning (if add_tokens_info=True), stack (sorted by score descending), and cost information.
#
#     Args:
#         llm_response (str): Model's response with "Reasoning:" and "Final Answer:" sections.
#         add_tokens_info (bool): If True, includes reasoning and uses "Cost" as the cost key.
#
#     Returns:
#         dict: Dictionary with keys:
#             - "Reasoning about Stack": Detailed reasoning (only if add_tokens_info=True).
#             - "Stack": String of technologies with scores, sorted by score descending (empty if none).
#             - "Cost" or "Cost_of_Stack_CV_extraction": Cost of the API call (always included).
#             - All keys from tokens_data (only if add_tokens_info=True).
#     """
#     # Extract and clean the response (remove token section)
#     cleaned_response, token_data = extract_and_parse_token_section(
#         response=llm_response,
#         additional_key_text="",
#         add_tokens_info=add_tokens_info
#     )
#
#     result = {}
#
#     # Extract reasoning if add_tokens_info=True
#     if add_tokens_info:
#         lines = cleaned_response.strip().split('\n')
#         reasoning_lines = []
#         for line in lines:
#             if line.startswith("Final Answer:"):
#                 break
#             reasoning_lines.append(line)
#         result["Reasoning about Stack"] = "\n".join(reasoning_lines).strip()
#
#     # Extract stack from "Final Answer:" line
#     stack_line = ""
#     lines = cleaned_response.strip().split('\n')
#     for line in lines:
#         if line.startswith("Final Answer:"):
#             stack_line = line.replace("Final Answer:", "").strip()
#             break
#
#     # Process stack line
#     if stack_line and stack_line != "No technologies specified":
#         # Split into individual technology-score pairs
#         tech_pairs = [pair.strip() for pair in stack_line.split(',') if pair.strip()]
#
#         # Parse each pair into (technology, score) tuples
#         tech_scores = []
#         for pair in tech_pairs:
#             if ' - ' in pair:
#                 tech_name, score_str = pair.rsplit(' - ', 1)
#                 tech_name = tech_name.strip()
#                 try:
#                     score = int(score_str.strip())
#                     tech_scores.append((tech_name, score))
#                 except ValueError:
#                     continue
#
#         # Sort technologies by score (descending)
#         tech_scores.sort(key=lambda x: x[1], reverse=True)
#
#         # Rebuild the sorted stack string
#         sorted_stack = ", ".join([f"{tech} - {score}" for tech, score in tech_scores])
#         result["Stack"] = sorted_stack
#     else:
#         result["Stack"] = ""
#
#     # Extract cost from token_data (always included)
#     if "Cost" in token_data:
#         if add_tokens_info:
#             # Append full tokens_data only if add_tokens_info=True
#             result.update(token_data)
#         else:
#             cost = float(token_data["Cost"].replace("$", ""))
#             result["Cost_of_Stack_CV_extraction"] = cost
#
#     return result
#
#
#
#
# def extract_cv_stack(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": (
#                 "You are an expert-level technical analyst and data extraction specialist. "
#                 "Your primary function is to parse IT resumes to identify and evaluate technical skills. "
#                 "**First, explain your reasoning step-by-step in bullet points.** "
#                 "Then, return ONLY the formatted list as requested by the user."
#             )
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Analyze the following resume text to generate a comprehensive list of the candidate's technology skills. "
#                 "**Explain your reasoning step-by-step**, then return the final output in the required format.\n\n"
#                 "**Your internal process must be:**\n"
#                 "1. **Comprehensive Scan:** Identify ALL mentions of technologies in the text.\n"
#                 "2. **Normalize Technology Names:** Use the format `Full Name (Abbreviation)` where applicable.\n"
#                 "3. **Evidence-Based Scoring:** Assign a proficiency score from 1 to 5 using the criteria below.\n\n"
#                 "**Scoring Criteria:**\n"
#                 "- **5 - Expert:** Technology used in **3+ projects** OR **Advanced certification + 2+ projects**.\n"
#                 "- **4 - Proficient:** Technology used in **2 projects** OR listed in 'Skills' + used in **1 project**.\n"
#                 "- **3 - Competent:** **Intermediate certification** OR listed in 'Skills' without project evidence.\n"
#                 "- **2 - Foundational:** Mentioned in **1 project** OR **Foundational certification**.\n"
#                 "- **1 - Mentioned:** Only peripheral mention.\n\n"
#                 "**Output Instructions:**\n"
#                 "1. **Reasoning:** [Your step-by-step analysis in bullet points].\n"
#                 "2. **Final Answer:** [Single line: `Technology (Abbreviation) - Score, ...` or `No technologies specified`].\n\n"
#                 "**Example Output:**\n"
#                 "Reasoning:\n"
#                 "- Found 'K8s' in 3 projects → Normalized to 'Kubernetes (K8s)' with score 5.\n"
#                 "- Found 'Python' in 'Skills' and 1 project → Score 4.\n"
#                 "Final Answer: Kubernetes (K8s) - 5, Python - 4\n\n"
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
#
#     print(response)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_cv_stack_response(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data

from pydantic import BaseModel, Field
from typing import List

from src.nlp.llm_handler import extract_and_parse_token_section, LLMHandler

class TechnologyItem(BaseModel):
    name: str = Field(description="Technology name in format 'Full Name (Abbreviation)' if applicable")
    score: int = Field(ge=1, le=5, description="Proficiency score from 1-5")
    # Убираем обязательное поле reasoning, так как модель его не возвращает

class CVStackAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    technologies: List[TechnologyItem] = Field(description="List of identified technologies with scores")

#
# def _fallback_cv_stack_parse(response: str, token_data: dict, add_tokens_info: bool) -> dict:
#     result = {}
#
#     if add_tokens_info:
#         result["Reasoning about Stack"] = "Unable to extract reasoning from response"
#         result.update(token_data)
#
#     result["Stack"] = ""
#
#     if "Cost" in token_data and not add_tokens_info:
#         cost = float(token_data["Cost"].replace("$", ""))
#         result["Cost_of_Stack_CV_extraction"] = cost
#
#     return result

def extract_cv_stack(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV technology stack - now with structured outputs by default.
    """

    prompt = [
        {
            "role": "system",
            "content": "You are an expert technical analyst specializing in IT resume analysis."
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to extract technology skills with proficiency scores.\n\n"
                f"**Scoring Criteria:**\n"
                f"- **5 - Expert:** 3+ projects OR Advanced certification + 2+ projects\n"
                f"- **4 - Proficient:** 2 projects OR Skills section + 1 project\n"
                f"- **3 - Competent:** Intermediate certification OR Skills section only\n"
                f"- **2 - Foundational:** 1 project OR Foundational certification\n"
                f"- **1 - Mentioned:** Peripheral mention only\n\n"
                f"Use format 'Full Name (Abbreviation)' where applicable.\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 200)

    # Try structured output first
    structured_response = llm_handler.get_answer(
            prompt, model=model, max_tokens=max_tokens,
            response_format=CVStackAnalysis
        )
    # Process structured response
    cv_analysis = structured_response['parsed']
    usage = structured_response['usage']
    cost_info = structured_response['cost']

    result = {}

    if add_tokens_info:
        result["Reasoning about Stack"] = "\n".join([f"• {step}" for step in cv_analysis.reasoning_steps])
        result["Model Used"] = model
        result["Completion Tokens"] = str(usage.completion_tokens)
        result["Prompt Tokens"] = str(usage.prompt_tokens)
        cached_tokens = usage.prompt_tokens_details.cached_tokens if hasattr(usage, 'prompt_tokens_details') else 0
        result["Cached Tokens"] = str(cached_tokens)
        result["Cost"] = f"${cost_info['total_cost']:.6f}"

    # Format stack string
    if cv_analysis.technologies:
        sorted_techs = sorted(cv_analysis.technologies, key=lambda x: x.score, reverse=True)
        stack_string = ", ".join([f"{tech.name} - {tech.score}" for tech in sorted_techs])
        result["Stack"] = stack_string
    else:
        result["Stack"] = ""

    if not add_tokens_info:
        result["Cost_of_Stack_CV_extraction"] = cost_info['total_cost']

    return result

