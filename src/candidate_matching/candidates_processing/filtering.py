
import pandas as pd

from src.candidate_matching.candidates_processing.filtering_by_location import filter_candidates_by_location
from src.candidate_matching.candidates_processing.filtering_by_technologies import filter_by_technologies
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

def filter_candidates_by_roles(df, required_roles):
    """
    Filters a DataFrame to retain only rows where the "Role" column contains at least one of the required roles as a substring.
    Args:
    - df (pd.DataFrame): The DataFrame to filter.
    - required_roles (str): A string of role substrings separated by newline characters.
    Returns:
    - pd.DataFrame: A filtered DataFrame containing only rows that match the criteria.
    """
    # Split the required_roles string into a list
    required_roles_list = required_roles.split('\n')
    # Create a boolean mask where any of the required_roles is a substring in the "Role" column
    mask = df['Role'].str.contains('|'.join(required_roles_list), case=False, na=False)
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
    # Step 1: Filter by location
    location_filtered_df = filter_candidates_by_location(df, vacancy_info.get("Extracted Location", "Any location"))
    logger.info(f"Number of candidates after location filtering: {len(location_filtered_df)}\n{get_names(location_filtered_df)}")

    # Step 2: Filter by seniority
    seniority_filtered_df = filter_candidates_by_seniority(location_filtered_df, vacancy_info.get("Extracted Seniority", "Any"))
    logger.info(f"Number of candidates after seniority filtering: {len(seniority_filtered_df)}\n{get_names(seniority_filtered_df)}")

    # Step 3-6: Filter by technologies
    tech_filtered_df, coverage_percentage = filter_by_technologies(vacancy_info, seniority_filtered_df)

    # Step 7: Filter by roles if roles are specified and the number of candidates exceeds the threshold
    required_roles = vacancy_info.get("Matched Roles", "")
    if required_roles and len(tech_filtered_df) > int(os.getenv("MIN_CANDIDATES_THRESHOLD", 0)):
        roles_filtered_df = filter_candidates_by_roles(tech_filtered_df, required_roles)
        logger.info(f"Number of candidates after role filtering: {len(roles_filtered_df)}\n{get_names(roles_filtered_df)}")
        if roles_filtered_df.empty:
            roles_filtered_df = tech_filtered_df
    else:
        roles_filtered_df = tech_filtered_df

    final_filtered_df = roles_filtered_df
    logger.info(f"Number of candidates after final filtering: {len(final_filtered_df)}")

    return final_filtered_df, coverage_percentage

