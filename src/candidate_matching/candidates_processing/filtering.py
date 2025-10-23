
import pandas as pd
from lxml.doctestcompare import strip

from src.candidate_matching.candidates_processing.filtering_by_location import filter_candidates_by_location
from src.candidate_matching.candidates_processing.filtering_by_rate import filter_candidates_by_rate
from src.candidate_matching.candidates_processing.filtering_by_technologies import filter_candidates_by_technologies
from src.logger import logger

import os
from dotenv import load_dotenv
load_dotenv()


def filter_candidates_by_seniority(df, required_seniority):
    # Determine the order of seniority levels
    seniority_order = ['Junior', 'Middle', 'Senior', 'Principal']
    # If 'Any' is specified, return the original DataFrame
    if required_seniority not in seniority_order:
        return df
    # Determine the range of seniority levels to filter on
    if required_seniority == 'Junior':
        # For Junior, select Junior and Middle
        allowed_seniorities = seniority_order[:2]
    elif required_seniority == 'Middle':
        # For Middle, select Junior, Middle, and Senior
        allowed_seniorities = seniority_order[:3]
    elif required_seniority == 'Senior':
        # For Senior, select Middle, Senior, and Principal
        allowed_seniorities = seniority_order[1:]
    elif required_seniority == 'Principal':
        # For Principal, select Senior and Principal
        allowed_seniorities = seniority_order[2:]
    # Filter candidates by seniority levels
    filtered_df = df[df['Seniority'].isin(allowed_seniorities)]
    return filtered_df

def filter_candidates_by_roles(df, required_roles_list):
    """
    Filters candidates by required roles.
    Creates a 'Matched Roles' column in the DataFrame with only the roles that match the required_roles_list.
    Keeps only candidates with at least one matching role.

    Args:
        df (DataFrame): DataFrame with candidates.
        required_roles_list (List[str]): List of required roles.

    Returns:
        DataFrame: Filtered DataFrame.
    """
    # Create 'Matched Roles' column by filtering roles from 'Role' column
    df['Matched Roles'] = df['Role'].apply(
        lambda roles: [
            role.strip()
            for role in roles.split(',')
            if role.strip() in required_roles_list
        ]
    )
    # Handle the case where 'No Role is specified' is the only role
    df['Matched Roles'] = df['Matched Roles'].apply(lambda matched_roles: matched_roles if matched_roles else [])

    if len(required_roles_list) == 1 and required_roles_list[0].startswith("No "):
        return df

    # Filter candidates: keep only those with at least one matching role
    mask = df['Matched Roles'].apply(lambda matched_roles: len(matched_roles) > 0)
    # Apply the mask to filter the DataFrame
    filtered_df = df.loc[mask, :].copy()
    return filtered_df


def filter_candidates_by_industries(df, required_industries):
    """
    Filters a DataFrame to retain only rows where the "Industries" column contains at least one of the required roles as a substring.
    Args:
    - df (pd.DataFrame): The DataFrame to filter.
    - required_industries (str): A string of Industries substrings separated by newline characters.
    Returns:
    - pd.DataFrame: A filtered DataFrame containing only rows that match the criteria.
    """
    # Split the required_industries string into a list
    required_industries_list = required_industries.split('\n')
    # Create a boolean mask where any of the required_industries is a substring in the "Industries" column
    mask = df['Industries'].str.contains('|'.join(required_industries_list), case=False, na=False)
    # Apply the mask to filter the DataFrame
    filtered_df = df[mask]
    return filtered_df

def get_names(df):
    names_string = ', '.join(df['Full Name'].astype(str))
    return names_string

def primary_filtering_by_vacancy(vacancy_info, df):
    """
    Filters candidates based on the given vacancy information.

    Args:
    - vacancy_info (dict): The vacancy description.
    - df (pd.DataFrame): DataFrame containing candidate data.

    Returns:
    - tuple: Filtered DataFrame with candidates meeting the criteria and coverage percentage.
    """
    MIN_CANDIDATES_THRESHOLD = int(os.getenv("MIN_CANDIDATES_THRESHOLD"))
    filter_history = []

    # Step 1: Filter by location
    location = vacancy_info.get("Extracted Location", "Any location")
    location_filtered_df = filter_candidates_by_location(df, location)
    candidates_count = len(location_filtered_df)
    candidates_names = get_names(location_filtered_df)
    filter_history.append(f"Location: {location} -> {candidates_count} candidates ({candidates_names})")
    logger.info(filter_history[-1])

    # Step 2: Filter by seniority
    seniority = vacancy_info.get("Extracted Seniority", "Any")
    seniority_filtered_df = filter_candidates_by_seniority(location_filtered_df, seniority)
    candidates_count = len(seniority_filtered_df)
    candidates_names = get_names(seniority_filtered_df)
    filter_history.append(f"Seniority: {seniority} -> {candidates_count} candidates ({candidates_names})")
    logger.info(filter_history[-1])

    # Step 3: Filter by roles if roles are specified and the number of candidates exceeds the number of candidates LLM is capable to process in one time
    required_roles = vacancy_info.get("Matched Roles", "")
    roles_filtered_df = filter_candidates_by_roles(seniority_filtered_df, required_roles)
    candidates_count = len(roles_filtered_df)
    candidates_names = get_names(roles_filtered_df)
    filter_history.append(f"Matched Roles: {', '.join(required_roles)} -> {candidates_count} candidates ({candidates_names})")
    logger.info(filter_history[-1])

    # Step 4
    rate = vacancy_info.get("Extracted Rate", "")
    rate_filtered_df = filter_candidates_by_rate(roles_filtered_df, rate)
    candidates_count = len(rate_filtered_df)
    candidates_names = get_names(rate_filtered_df)
    filter_history.append(f"Rate: {rate} -> {candidates_count} candidates ({candidates_names})")
    logger.info(filter_history[-1])
    # if len(rate_filtered_df) < MIN_CANDIDATES_THRESHOLD:
    #         rate_filtered_df = tech_filtered_df

    # Step 5: Filter by technologies
    tech_filtered_df, tech_filter_history_str = filter_candidates_by_technologies(rate_filtered_df, vacancy_info)
    filter_history.append(tech_filter_history_str)

    # Step 7: Filter by industries if industries are specified and the number of candidates exceeds the number of candidates LLM is capable to process in one time
    required_industries = vacancy_info.get("Extracted Industries", "")
    if required_industries and len(tech_filtered_df) > 30:
        industries_filtered_df = filter_candidates_by_industries(tech_filtered_df, required_industries)
        candidates_count = len(industries_filtered_df)
        candidates_names = get_names(industries_filtered_df)
        filter_history.append(f"Industries: {', '.join(required_industries)} -> {candidates_count} candidates ({candidates_names})")
        logger.info(filter_history[-1])
        if len(industries_filtered_df) < MIN_CANDIDATES_THRESHOLD:
            industries_filtered_df = tech_filtered_df
            filter_history.append(f"After Industries filtration less then {MIN_CANDIDATES_THRESHOLD} candidates left going back to Rate filtration list")
            logger.info(filter_history[-1])
    else:
        industries_filtered_df = tech_filtered_df

    final_filtered_df = industries_filtered_df
    logger.info(f"Number of candidates after final filtering: {len(final_filtered_df)}")

    if len(final_filtered_df) == len(df):
        final_filtered_df = pd.DataFrame(columns=final_filtered_df.columns)
    filter_history_str = "\n".join(filter_history)

    return final_filtered_df, filter_history_str

