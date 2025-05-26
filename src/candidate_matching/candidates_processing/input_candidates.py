import re
import numpy as np
import pandas as pd

from src.data_processing.jaccard_similarity import calculate_jaccard_similarity
from src.google_services.sheets import read_specific_columns
from src.nlp.embedding_handler import add_embeddings_column



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
        # "➕Added",
        # "🔓Ready to work with"
        # "🤝Interviewed",
        # "✅English checked",
        # "📄Proposed",
        # "🔄WorkING",
        # "🏁WorkED",
        "🚧Currently on hold",
        "💔Refused Further Work"
    }
    # Filter the DataFrame
    df['LVL of engagement'] = df['LVL of engagement'].astype(str).str.strip()
    filtered_df = df[df['LVL of engagement'].apply(lambda x: not any(
          calculate_jaccard_similarity(x, invalid_lvl) >= 0.8 for invalid_lvl in not_valid_engagement_levels
      ))]

    # filtered_df = filtered_df.drop('LVL of engagement', axis=1)
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
        'Stack', 'Industry', 'Expertise', 'Belarusian', 'English',
        'Works hrs/mnth', 'Location', 'CV (original)', 'CV White Label',
        'Entry wage rate (EWR)', 'Sell rate', 'Embedding','Role_Embedding','Stack_Embedding'
    ]

    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract)
    print("number of candidates after reading", len(df))
    df = filter_candidates_by_engagement(df)

    df['Full Name'] = df.apply(lambda row: f"{clean_and_extract_first_word(row['First Name'])} {clean_and_extract_first_word(row['Last Name'])}", axis=1)

    # Calculate 'margin' as the difference between 'Sell rate' and 'Entry wage rate (EWR)'
    df['Sell rate'] = df['Sell rate'].str.replace('$', '').str.replace(',', '.').str.replace('/hr', '').replace('', np.nan).astype(float)
    df['Entry wage rate (EWR)'] = df['Entry wage rate (EWR)'].str.replace('$', '').str.replace(',', '.').str.replace('/hr', '').replace('', np.nan).astype(float)
    df['margin'] = (df['Sell rate'] - df['Entry wage rate (EWR)']).round(2)
    # Format back to desired format
    df.loc[:, 'Sell rate'] = df['Sell rate'].apply(lambda x: f"${x:.2f}/&#8203;hr" if pd.notnull(x) else "_")
    df.loc[:, 'margin'] = df['margin'].apply(lambda x: f"≈${x:.2f}/&#8203;hr" if pd.notnull(x) else "_")
    df = df.drop('Entry wage rate (EWR)', axis=1)

    initial_count = len(df)
    df = df[~((df['Role'] == '') & (df['Stack'] == ''))]
    df = df[~((df['First Name'] == '') | (df['Last Name'] == ''))]

    df = add_embeddings_column(df, write_columns=False)

    # Replace '' -> '_' and '\n' -> ', '  in the entire DataFrame
    df = df.applymap(lambda x: '_' if isinstance(x, str) and x == '' else x)
    df = df.applymap(lambda x: x.replace('\n', ', ') if isinstance(x, str) else x)
    print("number of candidates after filtering", len(df))

    return df

