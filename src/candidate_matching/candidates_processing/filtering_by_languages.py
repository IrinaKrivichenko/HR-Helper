import re
import pandas as pd
from typing import List, Optional

from src.data_processing.nlp.languages_info import language_codes

def has_language(candidate_languages: str, language: str) -> bool:
    """
    Checks if a candidate knows a specific language.
    Args:
        candidate_languages (str): String of candidate's languages.
        language (str): Language to check.
    Returns:
        bool: True if the candidate knows the language, False otherwise.
    """
    if language == "English":
        return True
    return language in candidate_languages

def is_match(candidate_languages: str, requirement_type: str, required_languages: List[str]) -> bool:
    """
    Determines if a candidate matches the language requirements.
    Args:
        candidate_languages (str): String of candidate's languages.
        requirement_type (str): Type of language requirement.
        required_languages (List[str]): List of required languages.
    Returns:
        bool: True if the candidate matches the requirements, False otherwise.
    """
    if requirement_type == "No language requirements":
        return True
    elif requirement_type == "Single language required":
        return has_language(candidate_languages, required_languages[0])
    elif requirement_type == "All listed languages are required":
        return all(has_language(candidate_languages, lang) for lang in required_languages)
    elif requirement_type == "Any of the listed languages is required":
        return any(has_language(candidate_languages, lang) for lang in required_languages)
    else:
        return False


def convert_language_levels(language_string: str) -> str:
    """
    Converts a string of languages and their levels to a string of language codes and levels.

    Args:
        language_string (str): String of languages and their levels (e.g., "English B2, Ukrainian C1").

    Returns:
        str: String of language codes and levels (e.g., "EN-B2, UK-C1").
    """
    if not language_string.strip():
        return ""

    # Regular expression to search for language and level
    pattern = re.compile(r'(\w+)\s+([A-Za-z0-9]+)')
    def replace_match(match):
        language = match.group(1)
        level = match.group(2).upper()  # Ensure level is uppercase
        code = language_codes.get(language, language)
        return f"{code}-{level}"
    # Apply the replacement to the entire string
    result = pattern.sub(replace_match, language_string)
    return result

def filter_languages(
    candidate_languages: str,
    requirement_type: str,
    required_languages: List[str]
) -> str:
    """
    Filters candidate's languages to keep only relevant ones and converts them to language codes.

    Args:
        candidate_languages (str): String of candidate's languages.
        requirement_type (str): Type of language requirement.
        required_languages (List[str]): List of required languages.

    Returns:
        str: Filtered string of relevant languages in language code format.
    """
    candidate_lang_list = [lang.strip() for lang in candidate_languages.split(",")]

    if requirement_type == "No language requirements":
        # Keep only English, default to "EN-B1" if not specified
        english_level_str = next(
            (lang_level for lang_level in candidate_lang_list if lang_level.startswith("English ")),
            "English B1"
        )
        return convert_language_levels(english_level_str)
    else:
        # Keep English and required languages
        relevant_languages = []
        for lang_level in candidate_lang_list:
            try:
                lang = lang_level.split()[0]
                if lang == "English" or lang in required_languages:
                    relevant_languages.append(lang_level)
            except Exception as e:
                print(f"Debug: Error processing lang_level: {lang_level}, error: {e}")
                print(candidate_languages)
                continue
        # Convert relevant languages to language codes
        relevant_languages_str = ", ".join(relevant_languages)
        return convert_language_levels(relevant_languages_str)

def filter_candidates_by_languages(
    df: pd.DataFrame,
    vacancy_languages: List[str],
    languages_col: str = "Languages"
) -> pd.DataFrame:
    """
    Filters candidates based on vacancy language requirements and keeps only relevant languages.
    Args:
        df (pd.DataFrame): DataFrame with candidate data.
        vacancy_languages (List[str]): List of languages and requirement type from vacancy.
        languages_col (str): Name of the column with candidate languages.
    Returns:
        pd.DataFrame: Filtered DataFrame with matching candidates and relevant languages only.
    """
    # Extract requirement_type and required languages
    requirement_type = vacancy_languages[-1]
    required_languages = [lang.split()[0] for lang in vacancy_languages[:-1]]

    # Create a copy of vacancy_languages to avoid modifying the original list
    updated_vacancy_languages = vacancy_languages.copy()
    # Remove "Single language required" if it exists
    if "Single language required" in updated_vacancy_languages:
        updated_vacancy_languages.remove("Single language required")

    if len(df) == 0:
        return df, updated_vacancy_languages

    # Apply filtering
    df["Matches"] = df[languages_col].apply(
        lambda x: is_match(x, requirement_type, required_languages)
    )
    filtered_df = df[df["Matches"]].copy()
    # Apply language filtering to the relevant candidates
    filtered_df[languages_col] = filtered_df[languages_col].apply(
        lambda x: filter_languages(x, requirement_type, required_languages)
    )
    # Drop the temporary column
    filtered_df.drop(columns=["Matches"], inplace=True, errors="ignore")

    return filtered_df, updated_vacancy_languages



