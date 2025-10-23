from typing import List

import pandas as pd

from src.logger import logger
from src.data_processing.nlp.tokenization import get_tokens, create_tokens_set
import os
from dotenv import load_dotenv
load_dotenv()


def mitigate_cloud_technologies_impact(tech_list: List[str]) -> List[str]:
    """
    Processes a list of technologies to standardize cloud platform names.
    Replaces full cloud platform names with their abbreviations and removes conflicts.

    Args:
        tech_list: List of technology names (e.g., ["Amazon Web Services (AWS)", "Microsoft Azure (Azure)", "Python"]).

    Returns:
        List[str]: Processed list with standardized cloud platform names.
    """
    # Define cloud platforms and their abbreviations
    cloud_mapping = {
        "Amazon Web Services (AWS)": "AWS",
        "Microsoft Azure (Azure)": "Azure",
        "Google Cloud Platform (GCP)": "GCP",
        "AWS": "AWS",  # Ensure no duplicates if already abbreviated
        "Azure": "Azure",
        "GCP": "GCP"
    }
    # Define conflicting cloud platforms (only one should remain)
    cloud_platforms = {"AWS", "Azure", "GCP"}
    # Process the list
    processed_techs = []
    found_cloud_platforms = set()  # Track which cloud platforms are already included

    for tech in tech_list:
        # Replace full names with abbreviations
        if tech in cloud_mapping:
            abbreviated_tech = cloud_mapping[tech]
            # Skip if this cloud platform is already in the list
            if abbreviated_tech in found_cloud_platforms:
                continue
            processed_techs.append(abbreviated_tech)
            found_cloud_platforms.add(abbreviated_tech)
        else:
            # Check if the tech is a cloud platform abbreviation
            if tech in cloud_platforms:
                if tech in found_cloud_platforms:
                    continue
                processed_techs.append(tech)
                found_cloud_platforms.add(tech)
            else:
                processed_techs.append(tech)
    return processed_techs

def filter_technologies_by_vacancy_tokens(candidate_stack: str, vacancy_tokens: set) -> str:
    # Split the candidate stack into individual technologies
    technologies = [tech.strip() for tech in candidate_stack.split(',')]
    # Retain only those technologies in which at least one token from the vacancy was found
    filtered_techs = [
        tech for tech in technologies
        if any(token.lower() in tech.lower() for token in vacancy_tokens)
    ]
    return ', '.join(filtered_techs)

def calculate_tech_coverage(candidate_stack: str, vacancy_technologies_list: list) -> str:
    candidate_techs = [tech.strip() for tech in candidate_stack.split(',') if tech.strip()]
    candidate_count = len(candidate_techs)
    vacancy_count = len(vacancy_technologies_list)
    return f"{candidate_count}/{vacancy_count}"

def covered_percentage(vacancy_set: set, candidate_set: set) -> float:
    """
    Calculates the percentage of coverage of the vacancy requirements by a given candidate.
    """
    if not vacancy_set:
        return 0.0  # Avoid division by zero
    intersection = vacancy_set & candidate_set  # Find common elements
    return (len(intersection) / len(vacancy_set)) * 100  # Calculate percentage

def get_names(df):
    names_string = ', '.join(df['Full Name'].astype(str))
    if 'Coverage' in df.columns:
        min_coverage = df['Coverage'].min()
        max_coverage = df['Coverage'].max()
        names_string = f"{names_string}\nCoverage: {min_coverage}-{max_coverage}\n"
    return names_string


def filter_candidates_by_technologies(df, vacancy_info):
    """
    Filters candidates based on programming languages and technologies mentioned in the vacancy information.

    Args:
    - vacancy_info (dict): The vacancy description.
    - df (pd.DataFrame): DataFrame containing candidate data.

    Returns:
    - tuple: Filtered DataFrame and coverage percentage.
    """
    MIN_CANDIDATES_THRESHOLD = int(os.getenv("MIN_CANDIDATES_THRESHOLD"))
    coverage_percentage = "0%"
    vacancy_programming_languages = vacancy_info.get("Extracted Programming Languages", [])
    vacancy_programming_set = create_tokens_set(vacancy_programming_languages)
    vacancy_technologies = mitigate_cloud_technologies_impact(vacancy_info.get("Extracted Technologies", []))
    vacancy_technologies_set = create_tokens_set(vacancy_technologies)

    pl_thresholds = [90, 60, 30]
    tech_thresholds = [40, 30, 20, 10, 5]
    filter_history = []

    # Step 5: Get candidates with fully covered programming languages
    if vacancy_programming_set:
        df['Coverage'] = df['Stack'].apply(
            lambda x: covered_percentage(vacancy_programming_set, get_tokens(x))
        )
        partial_pl_coverage_df = pd.DataFrame()
        for threshold in pl_thresholds:
            partial_pl_coverage_df = df[df['Coverage'] >= threshold]
            candidates_count = len(partial_pl_coverage_df)
            candidates_names = get_names(partial_pl_coverage_df)
            filter_history.append(f"Programming languages coverage >= {threshold}%: {candidates_count} candidates ({candidates_names})")
            logger.info(filter_history[-1])
            if candidates_count >= MIN_CANDIDATES_THRESHOLD:
                break
    else:
        partial_pl_coverage_df = df
        filter_history.append("No programming languages specified in vacancy.")

    # Step 6: Get candidates with coverage of other technologies
    if vacancy_technologies_set and len(partial_pl_coverage_df) > MIN_CANDIDATES_THRESHOLD:
        partial_pl_coverage_df['Coverage'] = partial_pl_coverage_df['Stack'].apply(
            lambda x: covered_percentage(vacancy_technologies_set, get_tokens(x))
        )
        partial_tech_coverage_df = pd.DataFrame()
        for threshold in tech_thresholds:
            partial_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Coverage'] >= threshold]
            candidates_count = len(partial_tech_coverage_df)
            candidates_names = get_names(partial_tech_coverage_df)
            filter_history.append(f"Technologies coverage >= {threshold}%: {candidates_count} candidates ({candidates_names})")
            logger.info(filter_history[-1])
            if candidates_count >= MIN_CANDIDATES_THRESHOLD:
                break
        else:
            if len(partial_tech_coverage_df) < MIN_CANDIDATES_THRESHOLD:
                partial_tech_coverage_df = partial_pl_coverage_df
                filter_history.append(f"After Technologies filtration less then {MIN_CANDIDATES_THRESHOLD} candidates left going back to Programming languages filtration list")
    else:
        partial_tech_coverage_df = partial_pl_coverage_df
        filter_history.append(f"It is less then {MIN_CANDIDATES_THRESHOLD} candidates or NO technologies specified in vacancy.")

    filter_history_str = "\n".join(filter_history)

    all_vacancy_techs = (vacancy_info.get("Extracted Programming Languages", []) +
                         vacancy_info.get("Extracted Technologies", []) +
                         vacancy_info.get("Nice to have Programming Languages", []) +
                         vacancy_info.get("Nice to have Technologies", []))
    all_vacancy_tokens_set = create_tokens_set(all_vacancy_techs)
    partial_tech_coverage_df['_Stack'] = partial_tech_coverage_df['Stack'].apply(lambda stack: filter_technologies_by_vacancy_tokens(stack, all_vacancy_tokens_set))

    return partial_tech_coverage_df, filter_history_str

