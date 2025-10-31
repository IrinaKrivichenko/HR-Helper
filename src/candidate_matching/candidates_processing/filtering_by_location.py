import pandas as pd
from typing import List, Callable
from src.data_processing.nlp.countries_info import EU_COUNTRIES
from src.data_processing.emoji_processing import remove_emojis

def has_only_excluded_locations(locations_str: str, excluded_countries: List[str]) -> bool:
    """
    Checks if a candidate's locations contain only excluded countries.
    Args:
        locations_str (str): String of locations with emoji flags.
        excluded_countries (List[str]): List of excluded countries.
    Returns:
        bool: True if all candidate's locations are excluded, False otherwise.
    """
    candidate_countries = [
        remove_emojis(country.strip())
        for country in locations_str.split(',')
        if country.strip()
    ]
    return all(country in excluded_countries for country in candidate_countries)

def has_eu_country(locations_str: str) -> bool:
    """
    Checks if a candidate's locations contain at least one EU country.
    Args:
        locations_str (str): String of locations with emoji flags.
    Returns:
        bool: True if at least one EU country is found, False otherwise.
    """
    candidate_countries = [
        remove_emojis(country.strip())
        for country in locations_str.split(',')
        if country.strip()
    ]
    return any(country in EU_COUNTRIES for country in candidate_countries)

def has_valid_location(locations_str: str, valid_locations: List[str]) -> bool:
    """
    Checks if a candidate's locations contain at least one valid country from the requirements.
    Args:
        locations_str (str): String of locations with emoji flags.
        valid_locations (List[str]): List of valid locations from the requirements.
    Returns:
        bool: True if at least one valid location is found, False otherwise.
    """
    candidate_countries = [
        remove_emojis(country.strip())
        for country in locations_str.split(',')
        if country.strip()
    ]
    return any(country in valid_locations for country in candidate_countries)

def filter_candidates_by_location(df: pd.DataFrame, location_requirements: List[str]) -> pd.DataFrame:
    """
    Filters candidates based on location requirements.
    Args:
        df (pd.DataFrame): DataFrame with candidates, containing a 'Location' column.
        location_requirements (List[str]): List of location requirements from the vacancy.
    Returns:
        pd.DataFrame: Filtered DataFrame based on location requirements.
    """
    # Get the list of excluded countries (with 'NOT' prefix)
    excluded_countries = [
        country.replace('NOT ', '') for country in location_requirements
        if country.startswith('NOT ')
    ]
    # If there are excluded countries, filter candidates who only have those locations
    if excluded_countries:
        df = df[~df['Location'].apply(lambda x: has_only_excluded_locations(x, excluded_countries))]
        return df

    # If 'Remote' is in the requirements, return the original DataFrame
    if 'Remote' in location_requirements:
        return df

    # If 'European Union' is in the requirements, return candidates with at least one EU country
    if 'European Union' in location_requirements:
        df = df[df['Location'].apply(has_eu_country)]
        return df

    # If none of the previous conditions worked, return candidates with at least one country from the requirements
    valid_locations = [
        country for country in location_requirements
        if not country.startswith('NOT ') and country not in ['Remote', 'European Union']
    ]
    if valid_locations:
        df = df[df['Location'].apply(lambda x: has_valid_location(x, valid_locations))]
    return df


#
# def filter_candidates_by_location(df, location_requirements):
#     # List of European Union countries
#     eu_countries = EU_COUNTRIES.copy()
#
#
#     # If location requirements are "Any location", return original DataFrame
#     if "Any location" in location_requirements:
#         return df
#
#     # Create a temporary column with locations without emoji flags
#     df['Clean Location'] = df['Location'].apply(lambda x: [remove_emoji(loc.strip()) for loc in x.split(',')])
#
#     # Splitting location requirements by commas
#     location_list = [loc.strip() for loc in location_requirements.split(',')]
#
#     # Check if "European Union" is in the requirements
#     if "European Union" in location_list:
#         # Filter candidates whose countries are in the list of EU countries
#         df = df[df['Clean Location'].apply(lambda x: any(loc in eu_countries for loc in x))]
#
#     # Determine if the requirements contain countries with the prefix "NOT"
#     not_countries = [loc.replace("NOT ", "").strip() for loc in location_list if loc.startswith("NOT ")]
#     allowed_countries = [loc.strip() for loc in location_list if not loc.startswith("NOT ") and loc != "European Union"]
#
#     # If there are countries with the prefix "NOT", exclude rows where all locations are in not_countries
#     if not_countries:
#         df = df[df['Clean Location'].apply(lambda x: any(loc not in not_countries for loc in x))]
#
#     # If there are allowed countries, leave only rows where at least one location is in allowed_countries
#     if allowed_countries:
#         # Only apply allowed countries filter if European Union is not specified
#         if "European Union" not in location_list:
#             df = df[df['Clean Location'].apply(lambda x: any(loc in allowed_countries for loc in x))]
#
#     # Drop the temporary column
#     df.drop(columns=['Clean Location'], inplace=True)
#     return df