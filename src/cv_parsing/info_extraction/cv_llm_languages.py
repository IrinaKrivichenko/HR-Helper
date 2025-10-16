import time

from src.data_processing.nlp.languages_info import LanguageItem
from src.data_processing.nlp.translator import translate_text_with_llm

import concurrent.futures

import json
from pydantic import BaseModel, Field
from typing import List
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class CVLanguagesAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    resume_language: str = Field(description="Primary language of the resume (English, Russian, Belarusian, etc.)")
    languages: List[LanguageItem] = Field(description="List of languages with CEFR levels")


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
                f"Analyze this resume to identify languages and their proficiency levels mapped to CEFR standard  (A1, A2, B1, B2, C1, C2).\n\n"
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
                f"- Consider the candidate's location when assigning B1 level (e.g., if the candidate is in a country where the language is widely spoken, B1 is a reasonable default).\n"
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
    languages_analysis = _validate_english_level(languages_analysis)

    # Get cached tokens if available
    cached_tokens = 0
    if hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_tokens = usage.prompt_tokens_details.cached_tokens

    # Build result dictionary with all fields
    result = {
        "Belarusian": "",
        "English": "",
        "Other languages": "",
        "Reasoning about Languages": "\n".join(f"• {step}" for step in languages_analysis.reasoning_steps),
        "Model of_Languages_CV_extraction": model,
        "Completion Tokens of_Languages_CV_extraction": str(usage.completion_tokens),
        "Prompt Tokens _of_Languages_CV_extraction": str(usage.prompt_tokens),
        "Cached Tokens of_Languages_CV_extraction": str(cached_tokens),
        "Cost_of_Languages_CV_extraction": cost_info['total_cost'],
        "Resume Language": languages_analysis.resume_language,
    }

    # Check for English resume with no explicit languages
    resume_lang = languages_analysis.resume_language.lower()
    if resume_lang == "english" and not languages_analysis.languages:
        # Clean up "Other languages" field before logging
        del result["Other languages"]
        logger.info(
            f"Field extraction completed - Fields: 'Belarusian', 'English', 'Languages' | Response: {json.dumps(result, ensure_ascii=False)}")
        return result

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

    # Combine English and Other languages as per original logic
    if result["English"] and result["Other languages"]:
        result["English"] = ", ".join([result["English"], result["Other languages"]])
    elif result["Other languages"]:
        result["English"] = ", ".join(["A1", result["Other languages"]])

    # Clean up "Other languages" field as it's merged into English
    del result["Other languages"]

    # Log the complete response in a single entry
    logger.info(
        f"Field extraction completed - Fields: 'Belarusian', 'English', 'Languages' | Response: {json.dumps(result, ensure_ascii=False)}")

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

