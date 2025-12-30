import re
from datetime import datetime
from typing import Iterable, Set

import numpy as np
import pandas as pd

from src.data_processing.nlp.emoji_processing import extract_emoji
from src.google_services.sheets import read_specific_columns, write_specific_columns
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

def filter_candidates_by_engagement(df: pd.DataFrame, keyword=None, col: str = "LVL of engagement") -> pd.DataFrame:
    """
    Filters the DataFrame to include only rows where 'LVL of engagement' has specific values.
    Args:
    - df (pd.DataFrame): The DataFrame containing candidate data.
    Returns:
    - pd.DataFrame: A filtered DataFrame with only the relevant rows.
    """
    # Define the valid engagement levels
    red_engagement_levels = {
        # "➕Added",
        # "📡Pending Connection",
        # "🔗 In Connections",
        # "🚀 Actively Applying",
        # "⏳Pending Responsе",
        # "💬In Talks",
        # "🔓Ready to work with",
        # "🙋Eager Applicant",
        # "🤝Interviewed",
        # "✅English checked",
        # "📄Proposed",
        # "🔄WorkING",
        # "🏁WorkED",
        "💔 Refused Further Work",
        "🚧On hold",
        "📵 Candidate unreachable",
        "❌ Checked: fake detected",
        "🚨 Suspected fake",
        "💸Too expensive"
    }
    green_engagement_levels = {
        "🚀 Actively Applying",
        "🔓Ready to work with",
        "🙋Eager Applicant",
        "🤝Interviewed",
        "✅English checked",
        "📄Proposed",
        "🔄WorkING",
        "🏁WorkED"
    }
    yellow_engagement_levels = {
        "➕Added",
        "📡Pending Connection",
        "🔗 In Connections",
        "⏳Pending Responsе",
        "💬In Talks"
    }

    def build_emoji_set(levels: Iterable[str]) -> Set[str]:
        out = set()
        for lvl in levels:
            ems = extract_emoji(str(lvl))
            if ems:
                out.update(ems)  # ems — строка из эмодзи; добавляем по символам
        return out

    red_emojis = build_emoji_set(red_engagement_levels)
    yellow_emojis = build_emoji_set(yellow_engagement_levels)
    green_emojis = build_emoji_set(green_engagement_levels)
    df2 = df.copy()
    emoji_col = df2[col].astype(str).map(lambda s: extract_emoji(s) or "")

    def has_any(target_emojis: Set[str]) -> pd.Series:
        if not target_emojis:
            return pd.Series(False, index=df2.index)
        pattern = "|".join(map(re.escape, sorted(target_emojis)))
        return emoji_col.str.contains(pattern, regex=True, na=False)

    has_red = has_any(red_emojis)
    has_yellow = has_any(yellow_emojis)
    has_green = has_any(green_emojis)
    # Filtering logic based on keyword
    if keyword == "ALL":
        # Keep all those without red emojis
        keep_mask = ~has_red
    else:
        # Current logic: exclude red emojis and those with only yellow emojis
        keep_mask = (~has_red) & (~(has_yellow & ~has_green))
        available_from_condition = df2['Available From'].isna() | (df2['Available From'] == '')
        keep_mask = keep_mask & available_from_condition
    return df2.loc[keep_mask]



def clean_and_extract_first_word(name):
    cleaned_name = re.sub(r'[^a-zA-Z\s]', '', name)
    first_word = cleaned_name.split()[0] if cleaned_name else ''
    return first_word

def get_df_for_vacancy_search(keyword=None):

    # Define the columns to extract to find candidates for vacancy
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Available From',
        'Seniority',  'Main Roles', 'Additional Roles',
        'From', 'LinkedIn', 'Telegram', 'Phone', 'Email', 'WhatsApp',
        'Stack', 'Industries', 'Expertise', 'Languages',
        'Work hrs/mnth', 'Location', 'CV (original)', 'CV White Label',
        'Entry wage rate (EWR)', 'Sell rate'
    ]

    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract)
    logger.info(f"number of candidates after reading {len(df)}" )
    df = filter_candidates_by_engagement(df, keyword)


    df['Full Name'] = df.apply(lambda row: f"{clean_and_extract_first_word(row['First Name'])} {clean_and_extract_first_word(row['Last Name'])}", axis=1)
    df['Role'] = df['Main Roles'] # + ", " + df['Additional Roles']
    df.drop(columns=['Main Roles', 'Additional Roles'], inplace=True)

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


def check_and_update_past_available_dates():
    """
    A function for filtering rows where the date in the 'Available From' column has already passed.
    Returns a DataFrame without rows with past dates.
    """
    def is_date_past(date_str):
        if not isinstance(date_str, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_str):
            return False

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            return date < datetime.now().date()
        except:
            return False

    columns_to_extract = ['First Name', 'Last Name', 'LVL of engagement', 'Available From']
    df = read_specific_columns(columns_to_extract)
    df['is_past'] = df['Available From'].apply(is_date_past)
    df.loc[df['is_past'], 'Available From'] = ''
    df.drop(columns=['is_past'], inplace=True)
    write_specific_columns(df['Available From'])

