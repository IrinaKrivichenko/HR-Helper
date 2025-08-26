# from src.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler, extract_and_parse_token_section
#
# def parse_llm_cv_languages_response(response: str, add_tokens_info: bool = False) -> dict:
#     """
#     Parses the LLM response for a CV languages analysis.
#     Extracts reasoning (if add_tokens_info=True), languages with CEFR levels, and cost information.
#     Args:
#         response (str): Model's response with "Reasoning:" and "Final Answer:" sections.
#         add_tokens_info (bool): If True, includes reasoning and uses "Cost" as the cost key.
#     Returns:
#         dict: Dictionary with keys:
#             - "Reasoning about Languages": Detailed reasoning (only if add_tokens_info=True).
#             - "Belarusian": CEFR level for Belarusian (or empty string if not specified).
#             - "English": CEFR level for English (or empty string if not specified).
#             - "Other languages": String of other languages with levels (e.g., "German B2, Spanish A1").
#             - "Cost" or "Cost_of_Languages_CV_extraction": Cost of the API call (always included).
#             - All keys from tokens_data (only if add_tokens_info=True).
#     """
#     # Extract and clean the response (remove token section)
#     cleaned_response, token_data = extract_and_parse_token_section(
#         response=response,
#         additional_key_text=" cv_languages",
#         add_tokens_info=add_tokens_info
#     )
#
#     result = {
#         "Belarusian": "",
#         "English": "",
#         "Other languages": "",
#     }
#
#     # Extract reasoning if add_tokens_info=True
#     if add_tokens_info:
#         lines = cleaned_response.strip().split('\n')
#         reasoning_lines = []
#         for line in lines:
#             if line.startswith("Final Answer:"):
#                 break
#             reasoning_lines.append(line)
#         result["Reasoning about Languages"] = "\n".join(reasoning_lines).strip()
#
#     # Extract languages from "Final Answer:" line
#     final_answer = None
#     for line in cleaned_response.strip().split('\n'):
#         if line.startswith("Final Answer:"):
#             final_answer = line.replace("Final Answer:", "").strip()
#             break
#
#     # Extract cost from token_data (always included)
#     if "Cost" in token_data:
#         if add_tokens_info:
#             # Append full tokens_data only if add_tokens_info=True
#             result.update(token_data)
#         else:
#             cost = float(token_data["Cost"].replace("$", ""))
#             result["Cost_of_Languages_CV_extraction"] = cost  # Working mode: detailed key
#         return result
#
#     # Split the response into individual language-level pairs
#     language_pairs = [pair.strip() for pair in final_answer.split(',') if pair.strip()]
#     other_languages = []
#
#     for pair in language_pairs:
#         if ' ' in pair:
#             language, level = pair.rsplit(' ', 1)
#             language = language.strip()
#             level = level.strip()
#             # Assign to the appropriate category
#             if language.lower() == "belarusian":
#                 result["Belarusian"] = level
#             elif language.lower() == "english":
#                 result["English"] = level
#             else:
#                 other_languages.append(f"{language} {level}")
#
#     # Join other languages into a string
#     if other_languages:
#         result["Other languages"] = ", ".join(other_languages)
#
#     # Extract cost from token_data (always included)
#     if "Cost" in token_data:
#         if add_tokens_info:
#             # Append full tokens_data only if add_tokens_info=True
#             result.update(token_data)
#         else:
#             cost = float(token_data["Cost"].replace("$", ""))
#             result["Cost_of_Languages_CV_extraction"] = cost  # Working mode: detailed key
#     return result
#
#
# def extract_cv_languages(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": (
#                 "You are a multilingual HR analyst specializing in language proficiency assessment. "
#                 "Your function is to accurately extract all languages and their proficiency levels from a resume, mapping them to the CEFR standard. "
#                 "**First, explain your reasoning step-by-step in bullet points.** "
#                 "Then, return the final output in the required format."
#             )
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Analyze the following resume to identify the languages the candidate knows and their proficiency levels. "
#                 "**Explain your reasoning step-by-step**, then return the final output in the required format.\n\n"
#                 "**Your internal thought process for this task must be:**\n"
#                 "1. Scan the resume for a 'Languages' section or any mention of specific languages.\n"
#                 "2. For each language, identify its proficiency level (directly or by description).\n"
#                 "3. **Crucial Rule:** Map all descriptions to the CEFR scale (A1, A2, B1, B2, C1, C2) using the following logic:\n"
#                 "   - **Native / Родной:** → **C2**\n"
#                 "   - **Advanced / Proficient / Свободное владение:** → **C1**\n"
#                 "   - **Upper-Intermediate / Conversational / Fluent / Уверенный разговорный:** → **B2**\n"
#                 "   - **Intermediate / Средний:** → **B1**\n"
#                 "   - **Pre-Intermediate / Ниже среднего:** → **A2**\n"
#                 "   - **Elementary / Basic / Базовый:** → **A1**\n"
#                 "4. If a language is mentioned but no level can be inferred, exclude it from the final output.\n\n"
#                 "**Output Instructions:**\n"
#                 "1. **Reasoning:** [Your step-by-step analysis in bullet points].\n"
#                 "2. **Final Answer:** [Single line: `Language Level, Language Level` or `No languages specified`].\n\n"
#                 "**Example Output:**\n"
#                 "Reasoning:\n"
#                 "- Found 'English (fluent)' → Mapped to 'English C1'.\n"
#                 "- Found 'German B2' → Kept as is.\n"
#                 "Final Answer: English C1, German B2\n\n"
#                 "**Here is the CV:**\n"
#                 f"{cv}"
#             )
#         }
#     ]
#
#     # Calculate max tokens based on the length of the vacancy description
#     max_tokens = 200
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#
#     print(response)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_cv_languages_response(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data
#
#

from pydantic import BaseModel, Field
from typing import List, Optional

from src.nlp.llm_handler import extract_and_parse_token_section, LLMHandler
from src.nlp.translator import translate_text_with_llm


class LanguageItem(BaseModel):
    language: str = Field(description="Language name")
    level: str = Field(description="CEFR level (A1, A2, B1, B2, C1, C2)")

class CVLanguagesAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    resume_language: str = Field(description="Primary language of the resume (English, Russian, Belarusian, etc.)")
    languages: List[LanguageItem] = Field(description="List of languages with CEFR levels")


def extract_cv_languages(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV languages using Schema-Guided Reasoning approach with resume language detection.
    """

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a multilingual HR analyst specializing in language proficiency assessment. "
                "You MUST respond with valid JSON only, no additional text, markdown, or formatting."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to identify languages and their proficiency levels mapped to CEFR standard.\n\n"
                f"**IMPORTANT: First determine the primary language of the resume itself.**\n\n"
                f"**CEFR Mapping Rules:**\n"
                f"- Native/Родной → C2\n"
                f"- Advanced/Proficient/Свободное владение → C1\n"
                f"- Upper-Intermediate/Conversational/Fluent/Уверенный разговорный → B2\n"
                f"- Intermediate/Средний → B1\n"
                f"- Pre-Intermediate/Ниже среднего → A2\n"
                f"- Elementary/Basic/Базовый → A1\n\n"
                f"**Special Rules for English Level:**\n"
                f"- If resume is NOT written in English: English level is likely A1 unless explicitly stated\n"
                f"- If resume is NOT in English and English level is stated: cap it at maximum B1\n"
                f"- If resume IS in English: use stated level or infer from resume quality\n\n"
                f"**Rules:**\n"
                f"- Only include languages with identifiable proficiency levels\n"
                f"- If no level can be inferred, exclude the language\n"
                f"- Apply English level adjustment based on resume language\n\n"
                f"Respond ONLY with this JSON structure:\n"
                f"{{\n"
                f'  "reasoning_steps": ["Resume is written in Russian", "Found English (fluent) but capped at B1 due to non-English resume"],\n'
                f'  "resume_language": "Russian",\n'
                f'  "languages": [\n'
                f'    {{"language": "English", "level": "B1"}},\n'
                f'    {{"language": "Russian", "level": "C2"}}\n'
                f'  ]\n'
                f"}}\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    # Calculate max tokens
    max_tokens = 200

    # Get response from LLM
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    if not response:
        return {"Belarusian": "", "English": "", "Other languages": "", "Cost_of_Languages_CV_extraction": 0}

    print(response)  # Debug print

    # Extract and parse token section
    cleaned_response, token_data = extract_and_parse_token_section(
        response=response,
        additional_key_text=" cv_languages",
        add_tokens_info=add_tokens_info
    )

    # Parse JSON response
    try:
        import json

        # Clean the response
        cleaned_response = cleaned_response.strip()

        # Remove markdown code blocks if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        if not cleaned_response:
            return _fallback_cv_languages_parse(response, token_data, add_tokens_info)

        parsed_data = json.loads(cleaned_response)

        # Validate with Pydantic
        languages_analysis = CVLanguagesAnalysis(**parsed_data)

        # Apply additional English level validation based on resume language
        languages_analysis = _validate_english_level(languages_analysis)

    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON parsing failed: {e}")
        return _fallback_cv_languages_parse(response, token_data, add_tokens_info)

    # Build result dictionary in the original format
    result = {
        "Belarusian": "",
        "English": "",
        "Other languages": "",
    }

    if add_tokens_info:
        result["Reasoning about Languages"] = "\n".join([f"• {step}" for step in languages_analysis.reasoning_steps])
        result.update(token_data)

    # Process languages and categorize them
    other_languages = []

    for lang_item in languages_analysis.languages:
        language = lang_item.language.strip()
        level = lang_item.level.strip()

        if language.lower() == "belarusian":
            result["Belarusian"] = level
        elif language.lower() == "english":
            result["English"] = level
        else:
            other_languages.append(f"{language} {level}")

    # Join other languages into a string
    if other_languages:
        result["Other languages"] = ", ".join(other_languages)

    # Add cost info
    if "Cost" in token_data:
        if not add_tokens_info:
            cost = float(token_data["Cost"].replace("$", ""))
            result["Cost_of_Languages_CV_extraction"] = cost

    result = {
        "Belarusian": result["Belarusian"] ,
        "English": ", ".join([result["English"], result["Other languages"]]),
        # "Cost_of_Languages_CV_extraction": result["Cost_of_Languages_CV_extraction"]
              }

    return result


def _validate_english_level(analysis: CVLanguagesAnalysis) -> CVLanguagesAnalysis:
    """
    Validate and adjust English level based on resume language.
    """
    resume_lang = analysis.resume_language.lower()

    # If resume is not in English, apply restrictions
    if resume_lang not in ["english"]:
        for i, lang_item in enumerate(analysis.languages):
            if lang_item.language.lower() == "english":
                current_level = lang_item.level.upper()

                # If no explicit level was found, default to A1
                if not current_level or current_level == "":
                    analysis.languages[i].level = "A1"
                    analysis.reasoning_steps.append("English level defaulted to A1 (non-English resume)")

                # Cap English level at B1 for non-English resumes
                elif current_level in ["B2", "C1", "C2"]:
                    analysis.languages[i].level = "B1"
                    analysis.reasoning_steps.append(
                        f"English level capped at B1 (was {current_level}, non-English resume)")

    return analysis


def _fallback_cv_languages_parse(response: str, token_data: dict, add_tokens_info: bool) -> dict:
    """
    Fallback parser for CV languages extraction when JSON parsing fails.
    """
    result = {
        "Belarusian": "",
        "English": "",
        "Other languages": "",
    }

    if add_tokens_info:
        result["Reasoning about Languages"] = "Unable to extract reasoning from response"
        result.update(token_data)

    # Basic fallback: if we can't parse properly, assume non-English resume
    # and set English to A1 if mentioned
    if "english" in response.lower() and not result["English"]:
        result["English"] = "A1"

    if "Cost" in token_data and not add_tokens_info:
        cost = float(token_data["Cost"].replace("$", ""))
        result["Cost_of_Languages_CV_extraction"] = cost

    return result





from src.logger import logger
from src.nlp.llm_handler import LLMHandler

import concurrent.futures

def cv_languages_processing(cv_text: str, llm_handler: LLMHandler):
    # Use ThreadPoolExecutor to run the functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit both tasks to the executor
        future1 = executor.submit(extract_cv_languages, cv_text, llm_handler, model="gpt-4.1-nano")
        future2 = executor.submit(translate_text_with_llm, cv_text, llm_handler, model="gpt-4.1-nano")

        # Retrieve the results
        languages_extracted_data = future1.result()
        translated_text_info = future2.result()

    cv_text = translated_text_info['text']

    return cv_text, languages_extracted_data

