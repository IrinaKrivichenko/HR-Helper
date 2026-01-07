import os
import re

from langcodes import find_name
from telegram import Update

from src.bot.utils import send_answer_message
from src.data_processing.nlp.jaccard_similarity import find_most_similar_row
from src.google_services.sheets import read_specific_columns

import pandas as pd

def search_candidate_by_name(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """
    Search for a candidate by name in the DataFrame.
    Args:
        df (pd.DataFrame): DataFrame with candidate data.
        name (str): Name or part of the name to search for.
    Returns:
        pd.DataFrame: DataFrame with rows matching the name.
    """
    full_name_matches = df[df["Full Name"].str.contains(name, case=False, na=False)]
    if not full_name_matches.empty:
        return full_name_matches
    most_similar_index, most_similar_value = find_most_similar_row(df["Full Name"], name)
    if most_similar_index is not None:
        result = df.loc[[most_similar_index]]
        return result
    return pd.DataFrame()



def format_candidate_string(row, index):
    """
    Formats a single candidate row into a specified string format.
    Args:
    - row (pd.Series): A single row from the DataFrame containing candidate data.
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


    full_name = row['Full Name']
    available_from = row.get('Available From', '_')
    available_from = f" Available From {available_from}" if len(available_from)>2  else ""
    # Generate a link to a row in Google Sheets
    doc_id = os.getenv("STAFF_SPREADSHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    row_in_spreadsheets = row.get('Row in Spreadsheets', '')
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A{row_in_spreadsheets}'>{full_name}</a>"

    # Create a string for the candidate
    person_from = row.get('From', '_')
    engagement = row['LVL of engagement'] # extract_emoji(row['LVL of engagement'])
    seniority = row.get('Seniority', '_')
    roles = row.get('Main Roles', [])
    location = row.get('Location', '_')
    languages = row.get('Languages', '_')

    original = row.get('CV (original)', '_')
    cv = f"<a href='{original}'>CV</a>" if len(original)>2  else original
    white_label = row.get('CV White Label', '_')
    wl = f"<a href='{white_label}'>WL</a>" if len(white_label)>2  else white_label
    nda = row.get('NDA', '_')
    nda = f"<a href='{nda}'>NDA</a>" if len(nda)>2  else ""

    buy_rate = row.get('Entry wage rate (EWR)', '_')
    sell_rate = row.get('Sell rate', '_')
    margin = row.get('margin', '_') # Sell rate - EWR

    candidate_str = f"""
{index}. {google_sheet_row_link}{available_from} {person_from} {engagement} {seniority} {roles} {location} — {languages} {cv}/{wl} {contacts} {nda}
🟥{buy_rate} 🟨{sell_rate} 🟩{margin}"""
    return candidate_str

def generate_answer_for_candidates_df(df):
    list_of_candidate_strimg = []
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        candidate_strimg = format_candidate_string(row, index)
        list_of_candidate_strimg.append(candidate_strimg)
    return "\n\n".join(list_of_candidate_strimg)


async def process_names(update,  names_list, user_name, llm_handler=None):
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Available From',
        'Seniority', 'Main Roles', 'Additional Roles',
        'From', 'LinkedIn', 'Telegram', 'Phone', 'Email', 'WhatsApp',
        'Stack', 'Industries', 'Expertise', 'Languages',
        'Work hrs/mnth', 'Location', 'CV (original)', 'CV White Label',
        'Entry wage rate (EWR)', 'Sell rate', 'NDA'
    ]
    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract)
    df["Full Name"] = df["First Name"]+' '+ df["Last Name"]
    for name in names_list:
        name_df = search_candidate_by_name(df, name)
        answer_for_name = generate_answer_for_candidates_df(name_df)
        await send_answer_message(update, answer_for_name)
