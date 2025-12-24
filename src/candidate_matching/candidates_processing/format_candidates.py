import re
from typing import List

from src.data_processing.nlp.emoji_processing import extract_emoji
from src.data_processing.nlp.tokenization import create_tokens_set
from dotenv import load_dotenv
load_dotenv()
import os




def format_candidate_string(row, stack, index,  show_reasoning=False):
    """
    Formats a single candidate row into a specified string format.
    Args:
    - row (pd.Series): A single row from the DataFrame containing candidate data.
    - stack (str): The technology stack of the candidate.
    Returns:
    - str: A formatted string for the candidate.
    """

    def is_whatsapp_link(text: str) -> bool:
        # WhatsApp link format check
        # should start with “wa.me/”, “http://wa.me/”, “https://wa.me/” + phone number
        pattern = r'^(?:https?:\/\/)?wa\.me\/[1-9]\d{7,14}$'
        return bool(re.fullmatch(pattern, text))

    contacts_list = []
    if len(row['Telegram'])>2:
        contacts_list.append(f"<a href='{row['Telegram']}'>Telegram</a>")
    if len(row['WhatsApp'])>2:
        if is_whatsapp_link(row['WhatsApp']):
            contacts_list.append(f"<a href='{row['WhatsApp']}'>WhatsApp</a>")
        else:
            contacts_list.append(row['WhatsApp'])
    if len(row['LinkedIn'])>2 and len(contacts_list) < 3:
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
    doc_id = os.getenv("STAFF_SPREADSHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    row_in_spreadsheets = row.get('Row in Spreadsheets', '')
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A{row_in_spreadsheets}'>{full_name}</a>"

    # Create a string for the candidate
    suitability = int(float(row.get('Suitability Score', '0'))*100)
    person_from = row.get('From', '_')
    engagement = row['LVL of engagement'] # extract_emoji(row['LVL of engagement'])
    seniority = row.get('Seniority', '_')
    roles = ", ".join(row.get('Matched Roles', []))
    location = row.get('Location', '_')
    tech_coverage = ""# row.get('Tech Coverage', '')
    stack = row.get('_Stack', '_').replace("\n", ", ").replace(" ,", ",").replace(",,", ",")
    languages = row.get('Languages', '_')

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
    extracted_technologies_tokenized = create_tokens_set(extracted_technologies)
    for index, (_, row) in enumerate(df.iterrows(), start=start_index):
        # Extract common technologies
        stack = row.get('Stack', '')
        common_technologies = ''
        if stack:
            stack_values_tokenized = create_tokens_set(stack)
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
    show_reasoning = True
    # Process better_fit_df
    better_fit_df = generate_candidates_summary_for_df(better_fit_df, 1, extracted_technologies, show_reasoning)
    # Process lesser_fit_df with index starting after the last index of better_fit_df
    start_index = len(better_fit_df) + 1
    lesser_fit_df = generate_candidates_summary_for_df(lesser_fit_df, start_index, extracted_technologies, show_reasoning)
    return better_fit_df, lesser_fit_df


def format_tech_sting(extracted_technologies: List, nice_to_have_technologies: List, sep: str=" • "):
    extracted_technologies = sep.join(extracted_technologies)
    nice_to_have_technologies = sep.join(nice_to_have_technologies)
    if nice_to_have_technologies:
        extracted_technologies = f"{extracted_technologies} ✨ {nice_to_have_technologies}"
    if not extracted_technologies:
        extracted_technologies = "_"
    return extracted_technologies

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
    extracted_programming_languages = format_tech_sting(llm_extracted_data.get('Extracted Programming Languages', []),
                                                        llm_extracted_data.get('Nice to have Programming Languages', []))
    extracted_technologies = format_tech_sting(llm_extracted_data.get('Extracted Technologies', []),
                                               llm_extracted_data.get('Nice to have Technologies', []))

    # Combine programming languages and technologies
    extracted_role = llm_extracted_data.get('Extracted Role', '')
    # Extract location
    extracted_location = ", ".join(llm_extracted_data.get("Extracted Location", []))
    extracted_languages = ", ".join(llm_extracted_data.get("Extracted Languages", []))
    extracted_rate = llm_extracted_data.get("Extracted Rate", "No rate specified")

    # Get the minimum candidates threshold from environment variables
    min_candidates_threshold = 6  # Default value is 5 if not set

    # Form the final response
    if better_fit_summaries == "_" and lesser_fit_summaries == "_" and extracted_programming_languages == "_" and extracted_technologies == "_":
        telegram_response = f"{llm_extracted_data.get('Vacancy Reasoning', '_')}\n\n"
        return telegram_response
    else:
        telegram_response = (
            f"<b>📍 Location: </b>{extracted_location}\n"
            f"<b>🗣️ Languages: </b>{extracted_languages}\n"            
            f"<b>🧑‍💼 Role: </b>{extracted_role}\n"
            f"<b>🔣 ProgLang: </b>{extracted_programming_languages}\n"
            f"<b>🧰 Techs: </b>{extracted_technologies}\n"
            f"<b>💸 Rate: </b>{extracted_rate}\n"
        )

    if better_fit_summaries == "_" and lesser_fit_summaries == "_":
        telegram_response += "There are no candidates matching for the vacancy\n"
        telegram_response += 'Consider <a href="https://www.linkedin.com/my-items/posted-jobs/">adding hiring job post</a> to increase our DB.'
    else:
        telegram_response += f"\n<b>🎯 Best-fit:</b>{better_fit_summaries}\n"

        # Check if the number of lesser fit candidates exceeds the threshold
        if (len(better_fit_df) >= min_candidates_threshold or (len(better_fit_df)+len(lesser_fit_df)) >= 2*min_candidates_threshold):
            lesser_fit_summaries = "_"
        telegram_response += f"\n<b>🧩 Low-fit:</b>{lesser_fit_summaries}\n"

    return telegram_response

