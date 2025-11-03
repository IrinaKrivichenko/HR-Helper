import time

from src.data_processing.nlp.languages_info import LanguageItem
from src.data_processing.nlp.translator import translate_text_with_llm

import concurrent.futures

import json
from pydantic import BaseModel, Field
from typing import List, Annotated, Optional
from annotated_types import MinLen
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class CVLanguagesAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    resume_language: str = Field(description="Primary language of the resume")
    languages: Annotated[List[LanguageItem], MinLen(1)] = Field(description="List of languages with CEFR levels")
    location_reasoning: str = Field(description="Reasoning about the candidate's location and its impact on language levels")
    location_language: Optional[LanguageItem] = Field(description="Language of the candidate's location (if applicable)", default=None)

def extract_cv_languages(
        cv: str,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
):
    """
    Extract CV languages using Schema-Guided Reasoning approach with resume language detection.
    """
    prompt = [
        {
            "role": "system",
            "content": "You are a multilingual HR analyst specializing in language proficiency assessment."
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to identify languages and their proficiency levels mapped to CEFR standard (A1, A2, B1, B2, C1, C2).\n\n"
                f"**IMPORTANT: First determine the primary language of the resume itself.**\n\n"
                f"**CEFR Mapping Rules:**\n"
                f"- Native/Родной → C2\n"
                f"- Advanced/Proficient/Fluent → C1\n"
                f"- Upper-Intermediate/Conversational/Fluent/Confident → B2\n"
                f"- Intermediate/Средний → B1\n"
                f"- Pre-Intermediate/Ниже среднего → A2\n"
                f"- Elementary/Basic/Базовый → A1\n\n"
                f"**Special Rules for English Level:**\n"
                f"- If the resume is NOT in English: the English level is most likely A1 and definitely not higher than A2.\n"
                f"- If the resume is in English but other languages are clearly indicated: use this information.\n"
                f"- If the CV is in English but other languages are not clearly indicated: Infer from the quality of the CV and the candidate's location whether it is B1 or B2.\n"
                f"- If a language is listed but the proficiency level is unclear, default to B1.\n"
                f"- If the CV is in English but the English level is NOT explicitly stated: the English level is B1 or B2, but NEVER higher than B2.\n"
                f"- Consider the candidate's location when assigning B1 level (e.g., if the candidate is in a country where the language is widely spoken, B1 is a reasonable default).\n"
                f"- If the candidate's location is mentioned, include the language of that location and assign B1 level to it if not explicitly stated.\n"
                f"\n"
                f"**Rules:**\n"
                f"- Only include languages with identifiable proficiency levels\n"
                f"- If no level can be inferred, exclude the language\n"
                f"- Apply English level adjustment based on resume language\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    max_tokens = max(len(cv), 200)

    # Use structured output
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=max_tokens,
        response_format=CVLanguagesAnalysis
    )

    # Process structured response
    languages_analysis = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Apply validation
    languages_analysis = _validate_english_level(languages_analysis, cv)

    # Get cached tokens if available
    cached_tokens = 0
    if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    # Build result dictionary with all fields
    result = {
        "Languages": ", ".join([f"{lang.language} {lang.level}" for lang in languages_analysis.languages]),
        "Reasoning about Languages": (
                        "\n".join(f"• {step}" for step in languages_analysis.reasoning_steps) +
                        (f"\n\n• Location Reasoning:\n{languages_analysis.location_reasoning}"
                         if languages_analysis.location_reasoning else "")
                    ),
        "Model of_Languages_CV_extraction": model,
        "Completion Tokens of_Languages_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens _of_Languages_CV_extraction": str(usage.prompt_tokens),
        "Cached Tokens of_Languages_CV_extraction": str(cached_tokens),
        "Cost_of_Languages_CV_extraction": cost_info['total_cost'],
        "Resume Language": languages_analysis.resume_language,
    }
    return result


def _validate_english_level(languages_analysis: CVLanguagesAnalysis, cv: str) -> CVLanguagesAnalysis:
    """
    Validates the English level in the languages list.
    If the English level is C1 or C2 but the word "English" is not explicitly mentioned in the CV,
    the level is downgraded to B2.
    Args:
        languages_analysis (CVLanguagesAnalysis): Structured analysis of languages and their levels.
        cv (str): Raw text of the resume.
    Returns:
        CVLanguagesAnalysis: Updated analysis with validated English level.
    """
    # Check if "English" is explicitly mentioned in the CV (case-insensitive)
    has_explicit_english = "english" in cv.lower()
    # Iterate through all languages
    for lang in languages_analysis.languages:
        if lang.language.lower() == "english":
            # If the level is C1 or C2 but "English" is not explicitly mentioned in the CV
            if lang.level in ["C1", "C2"] and not has_explicit_english:
                lang.level = "B2"
            break  # Assume English is listed only once

    # Check if location_language is specified and not already in languages
    if languages_analysis.location_language:
        location_lang_name = languages_analysis.location_language.language
        is_location_lang_present = any(lang.language == location_lang_name for lang in languages_analysis.languages)
        if not is_location_lang_present:
            languages_analysis.languages.append(languages_analysis.location_language)

    return languages_analysis



def cv_languages_processing(cv_text: str, llm_handler: LLMHandler):
    start_time = time.time()
    # Use ThreadPoolExecutor to run the functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit both tasks to the executor
        future1 = executor.submit(extract_cv_languages, cv_text, llm_handler, model="gpt-4.1-nano")
        future2 = executor.submit(translate_text_with_llm, cv_text, llm_handler, model="gpt-4.1-nano")

        # Retrieve the results
        languages_extracted_data = future1.result()
        translated_text_info = future2.result()

    cv_text = translated_text_info['text']
    languages_extracted_data["Parsing Step1 Time (extract languages & translate)"] = time.time() - start_time
    return cv_text, languages_extracted_data

