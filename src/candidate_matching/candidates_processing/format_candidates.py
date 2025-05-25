import re

import os
from dotenv import load_dotenv

from src.nlp.tokenization import get_tokens

load_dotenv()

def format_candidate_string(row, stack, show_reasoning=False):
    """
    Formats a single candidate row into a specified string format.
    Args:
    - row (pd.Series): A single row from the DataFrame containing candidate data.
    - stack (str): The technology stack of the candidate.
    Returns:
    - str: A formatted string for the candidate.
    """
    contacts_list = []
    if len(row['Telegram'])>2:
        contacts_list.append(f"<a href='{row['Telegram']}'>Telegram</a>")
    if len(row['LinkedIn'])>2:
        contacts_list.append(f"<a href='{row['LinkedIn']}'>LinkedIn</a>")
    if len(row['Phone'])>2 and len(contacts_list) < 2:
        phone = row['Phone']
        phone = re.sub(r'[^\d+]', '', phone)
        contacts_list.append(f"<a href='tel:{phone}'>{phone}</a>" )
    if len(row['Email'])>2 and len(contacts_list) < 2:
        email = row['Email']
        contacts_list.append(f"<a href='mailto:{email}'>{email}</a>" )
    if len(contacts_list) < 2:
        contacts_list.append('_')
    contacts = " / ".join(contacts_list)

    if show_reasoning:
        reasoning = row['Reasoning'].replace("**", "<b>", 1).replace("**", "</b>", 1)
        reasoning = f"\n   ☻ {reasoning}"
    else:
        reasoning = ''
    # Generate a link to a row in Google Sheets
    doc_id = os.getenv("SHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    row_in_spreadsheets = row.get('Row in Spreadsheets', '')
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A{row_in_spreadsheets}'> Learn More…</a>"

    # Create a string for the candidate
    full_name = row['Full Name']
    engagement = row['LVL of engagement']
    seniority = row.get('Seniority', '_')
    location = row.get('Location', '_')
    person_from = row.get('From', '_')
    rate = row.get('Sell rate', '_')
    margin = row.get('margin', '_') # Sell rate - EWR
    english = row.get('English', '_')
    belarusian = row.get('Belarusian', '_')
    original = row.get('CV (original)', '_')
    original = f"<a href='{original}'>Original</a>" if len(original)>2 in row else original
    white_label = row.get('CV White Label', '_')
    white_label = f"<a href='{white_label}'>White Label</a>" if len(white_label)>2 in row else white_label

    stack = row.get('Stack', '_').replace("\n", ", ").replace(" ,", ",").replace(",,", ",")

    candidate_str = f"""{full_name} ({seniority}), {location}
   ☻ {engagement}
   ☻ From: {person_from}
   ☻ Sell rate: {rate} (margin: {margin})
   ☻ English: {english}, Belarusian: {belarusian}
   ☻ Stack: <code>{stack}</code>
   ☻ CV: {original} / {white_label}
   ☻ {contacts}{reasoning}
   ☻ {google_sheet_row_link}\n"""

    return candidate_str




# Dmitry Efremov (Senior), 🇮🇱Israel
# From: ProfUa (Elena Velbitskaya)
# Sell rate: $39/hr (margin: ≈$[Sell rate - EWR]/hr)
# English: B1-В2 German B1, Belarusian: C1
# Stack: Pandas, NumPy, PySpark, Tableau, Databricks, PowerBI, PySpark, Terraform, Airflow
# CV: Original / White Label
# 1st [Telegram](Максим ) /
# 2nd [LinkedIn](https://www.linkedin.com/in/elena-shamis-1a644642/) /
# 3rd (Optional if no tg&Lnkd) +972 53 321 9998 /
# 4th (Optional if no tg&Lnkd) elena.v.shamis@gmail.com
# (Always show 2 means of communication)
# (Optional: if less than 5 candidates) (Reasoning: 1-3 phrases)
# Learn More…

# Dmitry Efremov (Senior), 🇮🇱Israel
# From: ProfUa (Elena Velbitskaya)
# Sell rate: $39/hr (margin: ≈$10/hr)
# English: B1-В2 German B1, Belarusian: C1
# Stack: Pandas, NumPy, PySpark, Tableau, Databricks, PowerBI, PySpark, Terraform, Airflow
# CV: Original / White Label
# Telegram / LinkedIn
# Dmitry Efremov was selected as the top candidate because he is a Senior Python Developer with a strong focus on Python, which is a key requirement in the job description. He also has experience with various frameworks and tools that complement the role, such as Django and FastAPI, and he is located in Israel, which aligns with the job's location requirement. His English proficiency is at B1-B2 level, meeting the language requirement. Learn More…

def generate_candidates_summary(better_fit_df, lesser_fit_df, extracted_technologies):
    """
    Generates a summary for each candidate indicating which required technologies they possess.
    """
    def generate_candidates_summary_for_df(df, show_reasoning):
        summaries = []
        extracted_technologies_tokenized = get_tokens(extracted_technologies)
        for _, row in df.iterrows():
            # Extract common technologies
            stack = row.get('Stack', '')
            common_technologies = ''
            if stack:
                stack_values_tokenized = get_tokens(stack)
                common_technologies_tokenized = stack_values_tokenized.intersection(extracted_technologies_tokenized)
                common_technologies = ', '.join(common_technologies_tokenized)
            candidate_summary = format_candidate_string(row, common_technologies, show_reasoning)
            summaries.append(candidate_summary)
        # Add the summaries as a new column in the DataFrame
        df['Candidate Summary'] = summaries
        return df

    if len(better_fit_df) > int(os.getenv("MIN_CANDIDATES_THRESHOLD")):
        show_reasoning = False
    else:
        show_reasoning = True

    better_fit_df = generate_candidates_summary_for_df(better_fit_df, show_reasoning)
    lesser_fit_df = generate_candidates_summary_for_df(lesser_fit_df, show_reasoning)
    return better_fit_df, lesser_fit_df

def generate_final_response(better_fit_df, lesser_fit_df, extracted_technologies):
    """
    Generates the final response by splitting the DataFrame into two parts:
    those who are a better fit for the vacancy and those who are a slightly lesser fit.
    """
    def join_all_df_summaries(df):
        df_list = df['Candidate Summary'].tolist()
        if len(df_list):
            return "\n".join(df_list)
        else:
            return "_"

    better_fit_summaries = join_all_df_summaries(better_fit_df)
    lesser_fit_summaries = join_all_df_summaries(lesser_fit_df)

    # Form the final response
    final_response = f"Extracted technologies from the vacancy:\n {extracted_technologies}\n\nBetter Fit Candidates:\n {better_fit_summaries}\n\nLesser Fit Candidates: \n{lesser_fit_summaries}\n"
    return final_response