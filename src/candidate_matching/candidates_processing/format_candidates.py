import re

from src.data_processing.nlp.tokenization import get_tokens
from dotenv import load_dotenv
load_dotenv()

def format_candidate_string(row, stack, index,  show_reasoning=False):
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
        reasoning = f"\n   ➤ {reasoning}"
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
    original = f"<a href='{original}'>Original</a>" if len(original)>2  else original
    white_label = row.get('CV White Label', '_')
    white_label = f"<a href='{white_label}'>White Label</a>" if len(white_label)>2  else white_label


    stack = row.get('Stack', '_').replace("\n", ", ").replace(" ,", ",").replace(",,", ",")

    candidate_str = f"""{index}. {full_name} ({seniority}), {location}
   ➤ {engagement}
   ➤ From: {person_from}
   ➤ Sell rate: {rate} (margin: {margin})
   ➤ English: {english}, Belarusian: {belarusian}
   ➤ Stack: <code>{stack}</code>
   ➤ CV: {original} / {white_label}
   ➤ {contacts}{reasoning}
   ➤ {google_sheet_row_link}\n"""

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

def generate_candidates_summary_for_df(df, start_index, extracted_technologies, show_reasoning):
    summaries = []
    extracted_technologies_tokenized = get_tokens(extracted_technologies)
    for index, (_, row) in enumerate(df.iterrows(), start=start_index):
        # Extract common technologies
        stack = row.get('Stack', '')
        common_technologies = ''
        if stack:
            stack_values_tokenized = get_tokens(stack)
            common_technologies_tokenized = stack_values_tokenized.intersection(extracted_technologies_tokenized)
            common_technologies = ', '.join(common_technologies_tokenized)
        candidate_summary = format_candidate_string(row, common_technologies, index, show_reasoning)
        summaries.append(candidate_summary)
    # Add the summaries as a new column in the DataFrame
    df['Candidate Summary'] = summaries
    return df

def generate_candidates_summary(better_fit_df, lesser_fit_df, extracted_technologies):
    """
    Generates a summary for each candidate indicating which required technologies they possess.
    """
    # if len(better_fit_df) > int(os.getenv("MIN_CANDIDATES_THRESHOLD")):
    #     show_reasoning = False
    # else:
    #     show_reasoning = True
    show_reasoning = True

    # Process better_fit_df
    better_fit_df = generate_candidates_summary_for_df(better_fit_df, 1, extracted_technologies, show_reasoning)

    # Process lesser_fit_df with index starting after the last index of better_fit_df
    start_index = len(better_fit_df) + 1
    lesser_fit_df = generate_candidates_summary_for_df(lesser_fit_df, start_index, extracted_technologies, show_reasoning)

    return better_fit_df, lesser_fit_df

import os

def generate_final_response(better_fit_df, lesser_fit_df, llm_extracted_data):
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

    # Extract and format vacancy technologies
    extracted_programming_languages = llm_extracted_data.get('Extracted Programming Languages', '')
    extracted_technologies = llm_extracted_data.get('Extracted Technologies', '')

    # Combine programming languages and technologies
    extracted_technologies_text = f"{extracted_programming_languages}\n{extracted_technologies}"

    # Extract location
    extracted_location = llm_extracted_data.get('Extracted Location', 'Any location')

    # Get the minimum candidates threshold from environment variables
    min_candidates_threshold = int(os.getenv("MIN_CANDIDATES_THRESHOLD", 5))  # Default value is 5 if not set

    # Form the final response
    if better_fit_summaries == "_" and lesser_fit_summaries == "_" and extracted_technologies_text.strip() == "":
        final_response = f"{llm_extracted_data.get('Vacancy Reasoning', '_')}\n\n"
        return final_response
    else:
        final_response = (
            f"<u><b>Location:</b></u>\n{extracted_location}\n\n"
            f"<u><b>Technologies required for the vacancy:</b></u>\n{extracted_technologies_text}\n\n"
        )

    if better_fit_summaries == "_" and lesser_fit_summaries == "_":
        final_response += "There are no candidates matching for the vacancy in the specified location\n"
    else:
        final_response += f"<u><b>Better Fit Candidates:</b></u>\n\n{better_fit_summaries}\n\n"

        # Check if the number of lesser fit candidates exceeds the threshold
        if (len(better_fit_df) >= min_candidates_threshold or (len(better_fit_df)+len(lesser_fit_df)) >= 2*min_candidates_threshold):
            lesser_fit_summaries = "_"
        final_response += f"<u><b>Lesser Fit Candidates:</b></u>\n\n{lesser_fit_summaries}\n"

    return final_response

