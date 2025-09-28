
import os
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tzlocal import get_localzone

from src.data_processing.jaccard_similarity import calculate_jaccard_similarity
from src.google_services.sheets import read_specific_columns, initialize_google_sheets_api
from src.logger import logger
from src.data_processing.nlp.tokenization import get_tokens

load_dotenv()

def parse_date(date_str):
    if ' ' in date_str:
        date_part = date_str.split()[0]
    else:
        date_part = date_str
    return datetime.strptime(date_part, '%Y-%m-%d')

def check_existing_vacancy(vacancy_description):
    """
    Checks if a similar vacancy has been saved in the last VACANCY_CACHE_TIME days.

    Args:
    - vacancy_description (str): The vacancy description.

    Returns:
    - tuple or None: A tuple containing the row index and the user who added the vacancy if found, otherwise None.
    """
    some_days_ago = datetime.now() - timedelta(days=int(os.getenv("VACANCY_CACHE_TIME")))

    # Define columns to extract
    columns_to_extract = ["Date", "vacancy description", "first_answer",
                          "step1 num number of initial candidates"]

    # Read specific columns from the vacancies sheet
    vacancies_df = read_specific_columns(columns_to_extract, os.getenv("SEARCH_CACHE_SHEET_NAME"))

    # Convert the input vacancy description to a set of words
    input_word_set = get_tokens(vacancy_description)

    # Check each row for a similar vacancy
    for index, row in vacancies_df.iterrows():
        saved_date_str = row['Date']
        saved_date = parse_date(saved_date_str)

        # Check if the date is within the last VACANCY_CACHE_TIME days
        if saved_date < some_days_ago:
            break

        saved_description = row['vacancy description']

        # Convert the saved vacancy description to a set of words
        saved_word_set = get_tokens(saved_description)
        jaccard_similarity = calculate_jaccard_similarity(input_word_set, saved_word_set)
        # Check if the descriptions are similar
        if jaccard_similarity >= 0.99:
            return row
        if jaccard_similarity >= 0.8:
            del row['first_answer']
            return row  # Return the row index and the user

    return None


def prepare_logs_data(vacancy_description, vacancy_dict, user, current_date):
    total_cost = (
        float(vacancy_dict.get('Cost vacancy_details', 0)) +
        float(vacancy_dict.get('Cost vacancy_industries', 0)) +
        float(vacancy_dict.get('Cost vacancy_location', 0)) +
        float(vacancy_dict.get('Cost candidates_selection', 0))
    )

    logs_results = [
        current_date,
        vacancy_dict.get("error_logs", ""),
        vacancy_description,
        vacancy_dict.get("final_answer", ""),
        vacancy_dict.get("Vacancy Reasoning", ""),
        vacancy_dict.get("Extracted Seniority", ""),
        vacancy_dict.get("Extracted Role", ""),
        vacancy_dict.get("Matched Roles", ""),
        vacancy_dict.get("Extracted Programming Languages", ""),
        vacancy_dict.get("Extracted Technologies", ""),
        vacancy_dict.get("Extracted English Level", ""),
        vacancy_dict.get("Extracted Rate", ""),
        vacancy_dict.get("Extracted Expertise", ""),
        vacancy_dict.get("Extracted Industries", ""),
        vacancy_dict.get("Extracted Location", ""),
        vacancy_dict.get("Selected Candidates", ""),
        vacancy_dict.get("Reasoning", ""),
        vacancy_dict.get("step1_candidates_number", ""),
        vacancy_dict.get("technologies_coverage", ""),
        vacancy_dict.get("step3_candidates_number", ""),
        vacancy_dict.get("step4_candidates_number", ""),
        user,
        vacancy_dict.get("list_of_filtered_candidates", ""),
        f"{vacancy_dict.get('step0_time', 0):.1f} sec",
        f"{vacancy_dict.get('step1_time', 0):.1f} sec",
        f"{vacancy_dict.get('step2_time', 0):.1f} sec",
        f"{vacancy_dict.get('step3_time', 0):.1f} sec",
        f"{vacancy_dict.get('step4_time', 0):.1f} sec",
        f"{vacancy_dict.get('step5_time', 0):.1f} sec",
        f"{vacancy_dict.get('total_time', 0):.1f} sec",
        vacancy_dict.get("Model Used vacancy_details", ""),
        vacancy_dict.get("Cost vacancy_details", 0),
        vacancy_dict.get("Model Used vacancy_industries", ""),
        vacancy_dict.get("Cost vacancy_industries", 0),
        vacancy_dict.get("Model Used vacancy_location", ""),
        vacancy_dict.get("Cost vacancy_location", 0),
        vacancy_dict.get("Model Used candidates_selection", ""),
        vacancy_dict.get("Cost candidates_selection", 0),
        total_cost
    ]

    return logs_results

def prepare_cache_data(vacancy_description, vacancy_dict, current_date):
    cache_results = [
        current_date,
        vacancy_description,
        vacancy_dict.get("final_answer", ""),
        vacancy_dict.get("step1_candidates_number", "")
    ]

    return cache_results

def save_to_sheet(service, sheet_id, sheet_name, range_name, data):
    value_input_option = "RAW"
    value_range_body = {
        "majorDimension": "ROWS",
        "values": [data],
    }

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption=value_input_option,
        body=value_range_body
    ).execute()

def insert_new_row(service, sheet_id, sheet_name, sheet_index):
    insert_request = {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_index,
                        "dimension": "ROWS",
                        "startIndex": 1,
                        "endIndex": 2
                    }
                }
            }
        ]
    }

    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=insert_request).execute()
    return f"{sheet_name}!A2:AM2" if sheet_name == os.getenv("SEARCH_LOGS_SHEET_NAME") else f"{sheet_name}!A2:D2"

def save_vacancy_description(vacancy_description, existing_vacancy, vacancy_dict, user, service=None):
    if service is None:
        service = initialize_google_sheets_api()

    try:
        SHEET_ID = os.getenv("SHEET_ID")
        SEARCH_LOGS_SHEET_NAME = os.getenv("SEARCH_LOGS_SHEET_NAME")
        SEARCH_CACHE_SHEET_NAME = os.getenv("SEARCH_CACHE_SHEET_NAME")
        LOGS_SHEET_ID = os.getenv("LOGS_SHEET_ID")
        CACHE_SHEET_ID = os.getenv("CACHE_SHEET_ID")

        local_timezone = get_localzone()
        current_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        if existing_vacancy is not None:
            row_index = existing_vacancy['Row in Spreadsheets']
            range_logs = f"{SEARCH_LOGS_SHEET_NAME}!A{row_index}:AM{row_index}"
            range_cache = f"{SEARCH_CACHE_SHEET_NAME}!A{row_index}:D{row_index}"
        else:
            range_logs = insert_new_row(service, SHEET_ID, SEARCH_LOGS_SHEET_NAME, LOGS_SHEET_ID)
            range_cache = insert_new_row(service, SHEET_ID, SEARCH_CACHE_SHEET_NAME, CACHE_SHEET_ID)

        logs_data = prepare_logs_data(vacancy_description, vacancy_dict, user, current_date)
        cache_data = prepare_cache_data(vacancy_description, vacancy_dict, current_date)

        save_to_sheet(service, SHEET_ID, SEARCH_LOGS_SHEET_NAME, range_logs, logs_data)
        save_to_sheet(service, SHEET_ID, SEARCH_CACHE_SHEET_NAME, range_cache, cache_data)

        logger.info("Results saved to Google Sheets.")

    except HttpError as err:
        logger.error(f"An error occurred: {err}")
