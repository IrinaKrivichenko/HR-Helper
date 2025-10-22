import re

from src.data_processing.emoji_processing import extract_emoji
from src.data_processing.nlp.languages_info import language_codes
from src.data_processing.nlp.tokenization import get_tokens
from dotenv import load_dotenv
load_dotenv()

def convert_language_levels(language_string):
    # Regular expression to search for language and level
    pattern = re.compile(r'(\w+)\s+([A-Za-z0-9]+)')
    def replace_match(match):
        language = match.group(1)
        level = match.group(2)
        code = language_codes.get(language, language)
        return f"{code}-{level}"
    # Apply the replacement to the entire string
    result = pattern.sub(replace_match, language_string)
    return result


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
        reasoning = f"{reasoning}"
    else:
        reasoning = ''

    full_name = row['Full Name']
    # Generate a link to a row in Google Sheets
    doc_id = os.getenv("SHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    row_in_spreadsheets = row.get('Row in Spreadsheets', '')
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A{row_in_spreadsheets}'>{full_name}</a>"

    # Create a string for the candidate
    suitability = int(float(row.get('Suitability Score', '0'))*100)
    person_from = row.get('From', '_')
    engagement = extract_emoji(row['LVL of engagement'])
    seniority = row.get('Seniority', '_')
    roles = ", ".join(row.get('Matched Roles', []))
    location = row.get('Location', '_')
    tech_coverage = ""# row.get('Tech Coverage', '')
    stack = row.get('Stack', '_').replace("\n", ", ").replace(" ,", ",").replace(",,", ",")
    languages = row.get('English', '_')
    if len(languages) > 2:
        languages = f" English {languages}"
        languages = convert_language_levels(languages)

    original = row.get('CV (original)', '_')
    cv = f"<a href='{original}'>CV</a>" if len(original)>2  else original
    white_label = row.get('CV White Label', '_')
    wl = f"<a href='{white_label}'>WL</a>" if len(white_label)>2  else white_label

    buy_rate = row.get('Entry wage rate (EWR)', '_')
    sell_rate = row.get('Sell rate', '_')
    margin = row.get('margin', '_') # Sell rate - EWR


    candidate_str = f"""
{index}. {google_sheet_row_link} {suitability}% {person_from} {engagement} {seniority} {roles} {location} — {tech_coverage} <code>{stack}</code> {languages} {cv}/{wl} {contacts}
{reasoning}
🟥{buy_rate} 🟨{sell_rate} 🟩{margin}"""

    return candidate_str



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
    extracted_programming_languages = extracted_programming_languages.replace(", ", " • ")
    extracted_technologies = llm_extracted_data.get('Extracted Technologies', '')
    extracted_technologies = extracted_technologies.replace(", ", " • ")
    # Combine programming languages and technologies
    extracted_technologies_text = f" • ".join([extracted_programming_languages, extracted_technologies])
    extracted_role = llm_extracted_data.get('Extracted Role', '')
    # Extract location
    extracted_location = llm_extracted_data.get('Extracted Location', 'Any location')
    extracted_rate = llm_extracted_data.get("Extracted Rate", "No rate specified")

    # Get the minimum candidates threshold from environment variables
    min_candidates_threshold = int(os.getenv("MIN_CANDIDATES_THRESHOLD", 5))  # Default value is 5 if not set

    # Form the final response
    if better_fit_summaries == "_" and lesser_fit_summaries == "_" and extracted_technologies_text.strip() == "":
        telegram_response = f"{llm_extracted_data.get('Vacancy Reasoning', '_')}\n\n"
        return telegram_response
    else:
        telegram_response = (
            f"<b>📍 Location: </b>{extracted_location}\n"
            f"<b>🧑‍💼 Role: </b>{extracted_role}\n"
            f"<b>🔣 ProgLang: </b>{extracted_programming_languages}\n"
            f"<b>🧰 Techs: </b>{extracted_technologies}\n"
            f"<b>💸 Rate: </b>{extracted_rate}\n"
        )

    if better_fit_summaries == "_" and lesser_fit_summaries == "_":
        telegram_response += "There are no candidates matching for the vacancy in the specified location\n"
        telegram_response += 'Consider <a href="https://www.linkedin.com/my-items/posted-jobs/">adding hiring job post</a> to increase our DB.'
    else:
        telegram_response += f"\n<b>🎯 Best-fit:</b>{better_fit_summaries}\n"

        # Check if the number of lesser fit candidates exceeds the threshold
        if (len(better_fit_df) >= min_candidates_threshold or (len(better_fit_df)+len(lesser_fit_df)) >= 2*min_candidates_threshold):
            lesser_fit_summaries = "_"
        telegram_response += f"\n<b>🧩 Low-fit:</b>{lesser_fit_summaries}\n"

    return telegram_response

