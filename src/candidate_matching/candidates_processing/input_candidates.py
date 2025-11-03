import re
import numpy as np
import pandas as pd

from src.data_processing.emoji_processing import extract_emoji
from src.data_processing.jaccard_similarity import calculate_jaccard_similarity
from src.google_services.sheets import read_specific_columns
from src.logger import logger

# Function to extract currency symbol from string
def extract_currency(value):
    if pd.isna(value) or value == '':
        return None
    # Search for currency symbols at the beginning of string
    currency_match = re.match(r'^([^\d\s]+)', str(value))
    return currency_match.group(1) if currency_match else '$'

# Function to extract numeric value from string
def extract_numeric_value(value):
    if pd.isna(value) or value == '':
        return np.nan
    # Remove all characters except digits, dots and commas
    numeric_str = re.sub(r'[^\d.,]', '', str(value))
    # Replace commas with dots for standardization
    numeric_str = numeric_str.replace(',', '.')
    try:
        return float(numeric_str)
    except ValueError:
        return np.nan

def filter_candidates_by_engagement(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters the DataFrame to include only rows where 'LVL of engagement' has specific values.

    Args:
    - df (pd.DataFrame): The DataFrame containing candidate data.

    Returns:
    - pd.DataFrame: A filtered DataFrame with only the relevant rows.
    """
    # Define the valid engagement levels
    not_valid_engagement_levels = {
        # "➕ Added",
        # "📡 Pending Connection",
        # "🔗 Added to Connections",
        # "🚀 Actively Applying",
        # "⏳ Pending Responsе",
        # "💬 In Talks",
        # "🔓 Ready to work with",
        # "🙋 Eager Applicant",
        # "🤝 Interviewed",
        # "✅ English checked",
        # "📄 Proposed",
        # "🔄 WorkING",
        # "🏁 WorkED",
        "💔 Refused Further Work",
        "🚧On hold",
        "📵 Candidate unreachable",
        "❌ Checked: fake detected"
    }
    forbidden_emojis = set()
    for level in not_valid_engagement_levels:
        emojis = extract_emoji(level)
        if emojis:
            forbidden_emojis.update(emojis)

    # Function for checking for prohibited emojis
    def contains_forbidden_emoji(text):
        emojis_in_text = extract_emoji(str(text))
        if emojis_in_text:
            return any(forbidden in emojis_in_text for forbidden in forbidden_emojis)
        return False

    # Filter the DataFrame
    df['LVL of engagement'] = df['LVL of engagement'].astype(str).str.strip()
    filtered_df = df[~df['LVL of engagement'].apply(contains_forbidden_emoji)]
    return filtered_df


def clean_and_extract_first_word(name):
    cleaned_name = re.sub(r'[^a-zA-Z\s]', '', name)
    first_word = cleaned_name.split()[0] if cleaned_name else ''
    return first_word

def get_df_for_vacancy_search():

    # Define the columns to extract to find candidates for vacancy
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Seniority', 'Role',
        'From', 'LinkedIn', 'Telegram', 'Phone', 'Email',
        'Stack', 'Industries', 'Expertise', 'Languages',
        'Work hrs/mnth', 'Location', 'CV (original)', 'CV White Label',
        'Entry wage rate (EWR)', 'Sell rate'
    ]

    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract)
    logger.info(f"number of candidates after reading {len(df)}" )
    df = filter_candidates_by_engagement(df)

    df['Full Name'] = df.apply(lambda row: f"{clean_and_extract_first_word(row['First Name'])} {clean_and_extract_first_word(row['Last Name'])}", axis=1)

    # Calculate 'margin' as the difference between 'Sell rate' and 'Entry wage rate (EWR)'
    df['sell_rate_numeric'] = df['Sell rate'].apply(extract_numeric_value)
    df['ewr_numeric'] = df['Entry wage rate (EWR)'].apply(extract_numeric_value)
    df['ewr_currency'] = df['Entry wage rate (EWR)'].apply(extract_currency)
    df['margin_numeric'] = (df['sell_rate_numeric'] - df['ewr_numeric']).round(2)
    # Format margin column with currency from EWR
    df['margin'] = df.apply(
        lambda row: f"≈{row['ewr_currency']}{row['margin_numeric']:.2f}/hr"
        if pd.notnull(row['margin_numeric']) and pd.notnull(row['ewr_currency']) else "_",
        axis=1
    )
    df = df.drop(['sell_rate_numeric', 'ewr_numeric', 'ewr_currency', 'margin_numeric'], axis=1)

    initial_count = len(df)
    df = df[~((df['Role'] == '') & (df['Stack'] == ''))]
    df = df[~((df['First Name'] == '') | (df['Last Name'] == ''))]

    # Remove ratings (numbers after dash) from Stack column
    df['Stack'] = df['Stack'].apply(
        lambda x: re.sub(r'\s*-\s*\d+', '', str(x)) if pd.notnull(x) else x
    )

    # Replace '' -> '_' and '\n' -> ', '  in the entire DataFrame
    df = df.applymap(lambda x: '_' if isinstance(x, str) and x == '' else x)
    df = df.applymap(lambda x: x.replace('\n', ', ') if isinstance(x, str) else x)
    logger.info(f"number of candidates after filtering {len(df)}")

    return df

