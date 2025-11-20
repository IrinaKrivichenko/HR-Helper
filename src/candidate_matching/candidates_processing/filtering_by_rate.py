import re

import pandas as pd

# Constants for currency conversion
EUR_TO_USD = 1.10466
GBP_TO_USD = 1.33

# Function to convert candidate's rate to USD
def convert_to_usd(rate_str):
    """
    Converts candidate's rate to USD.
    Args:
        rate_str: String in format like '$65.00/hr', '€33.00/hr', or '_'.
    Returns:
        float: Rate in USD, or None if rate is not specified or cannot be converted.
    """
    # Handle missing or unspecified rate
    if pd.isna(rate_str) or rate_str.strip() in ('_', 'No rate specified', ''):
        return None

    try:
        # Extract currency symbol and numeric value
        currency_symbol = rate_str[0]  # First character is the currency symbol
        numeric_str = re.search(r'\d+\.?\d*', rate_str).group()  # Extract numeric value
        # Convert to float
        rate_value = float(numeric_str)
        # Convert to USD based on currency
        if currency_symbol == '$':
            return rate_value
        elif currency_symbol == '€':
            return rate_value * EUR_TO_USD
        elif currency_symbol == '£':
            return rate_value * GBP_TO_USD
        else:
            return None  # Unknown currency
    except Exception:
        return None  # Return None if conversion fails


def filter_candidates_by_rate(df, vacancy_rate_str: str, rate_tolerance:int=5):
    """
    Filters candidates based on their sell rate compared to the vacancy rate.
    Args:
        df: DataFrame with candidate data.
        vacancy_rate_str: Rate from the vacancy in the format "{value} {currency} {period}".
        rate_tolerance: the maximum amount of $ that can be increased in the vacancy
    Returns:
        Filtered DataFrame.
    """

    # Parse vacancy rate
    if vacancy_rate_str == "No rate specified" or "per hour" not in vacancy_rate_str:
        return df  # No filtering if vacancy rate is not specified

    vacancy_rate_parts = vacancy_rate_str.split()
    vacancy_value = float(vacancy_rate_parts[0])
    vacancy_currency = vacancy_rate_parts[1]

    # Convert vacancy rate to USD for comparison
    if vacancy_currency == "€":
        vacancy_value_usd = vacancy_value * EUR_TO_USD
    elif vacancy_currency == "£":
        vacancy_value_usd = vacancy_value * GBP_TO_USD
    else:  # Default to USD
        vacancy_value_usd = vacancy_value

    # Calculate maximum allowed rate
    max_allowed_rate = vacancy_value_usd + rate_tolerance
    # Apply conversion to candidate rates
    df['Rate USD'] = df['Entry wage rate (EWR)'].apply(convert_to_usd)
    # Filter candidates:
    # 1. Keep candidates with no rate specified
    # 2. Keep candidates with rate <= max_allowed_rate
    filtered_df = df[
        (df['Entry wage rate (EWR)'].isna()) |
        (df['Rate USD'] <= max_allowed_rate)
    ]
    # Drop temporary column
    filtered_df = filtered_df.drop(columns=['Rate USD'])
    return filtered_df
