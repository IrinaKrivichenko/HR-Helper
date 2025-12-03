import pandas as pd
from typing import List
from src.data_processing.nlp.countries_info import EU_COUNTRIES
from src.data_processing.nlp.emoji_processing import remove_emojis

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

    # If none of the previous conditions worked, return candidates with at least one country from the requirements
    valid_locations = [
        country for country in location_requirements
        if not country.startswith('NOT ') and country not in ['Remote', 'European Union']
    ]
    # If 'European Union' is in the requirements, return candidates with at least one EU country
    if 'European Union' in location_requirements:
        valid_locations.extend(EU_COUNTRIES)
    if valid_locations:
        df = df[df['Location'].apply(lambda x: has_valid_location(x, valid_locations))]

    return df


