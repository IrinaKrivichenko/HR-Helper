
import os
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tzlocal import get_localzone

from src.data_processing.jaccard_similarity import calculate_jaccard_similarity
from src.google_services.sheets import read_specific_columns, initialize_google_sheets_api
from src.logger import logger
from src.nlp.tokenization import get_tokens

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
                          "step1 num number of initial candidates", "user"]

    # Read specific columns from the vacancies sheet
    vacancies_df = read_specific_columns(columns_to_extract, os.getenv("VACANCIES_SHEET_NAME"))

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

def save_vacancy_description(vacancy_description, existing_vacancy, vacancy_dict, user, service=None):
    """
    Saves the vacancy description and related data to Google Sheets.
    """
    for k in vacancy_dict:
        print(f'{k}')

    # Initialize the Google Sheets API
    if service is None:
        service = initialize_google_sheets_api()

    try:
        SHEET_ID = os.getenv("SHEET_ID")
        VACANCIES_SHEET_NAME = os.getenv("VACANCIES_SHEET_NAME")
        VACANCIES_SHEET_ID = os.getenv("VACANCIES_SHEET_ID")

        if existing_vacancy is not None:
            # If a similar vacancy exists, unpack the result and update the existing row
            row_index = existing_vacancy['Row in Spreadsheets']
            range_db = f"{VACANCIES_SHEET_NAME}!A{row_index}:AM{row_index}"
            user = f"{existing_vacancy['user']}\n{user}"
        else:
            # Otherwise, insert a new row at the second position
            insert_request = {
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": VACANCIES_SHEET_ID,
                                "dimension": "ROWS",
                                "startIndex": 1,
                                "endIndex": 2
                            }
                        }
                    }
                ]
            }
            service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=insert_request).execute()
            range_db = f"{VACANCIES_SHEET_NAME}!A2:AM2"

        value_input_option = "RAW"
        local_timezone = get_localzone()
        current_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        # Calculate total cost
        total_cost = (
            float(vacancy_dict.get('Cost vacancy_details', 0)) +
            float(vacancy_dict.get('Cost vacancy_industry', 0)) +
            float(vacancy_dict.get('Cost vacancy_location', 0)) +
            float(vacancy_dict.get('Cost candidates_selection', 0))
        )

        results = [
            current_date,  # 'Date': 'A',
            vacancy_dict.get("error_logs", ""),  # 'llm errors': 'B',
            vacancy_description,  # 'vacancy description': 'C',
            vacancy_dict.get("final_answer", ""),  # 'first_answer': 'D',
            vacancy_dict.get("Vacancy Reasoning", ""),  # 'llm Vacancy Reasoning': 'E',
            vacancy_dict.get("Extracted Seniority", ""),  # 'llm extracted Seniority': 'F',
            vacancy_dict.get("Extracted Role", ""),  # 'llm extracted role': 'G',
            vacancy_dict.get("Matched Roles", ""),  # 'llm Matched Roles': 'H',
            vacancy_dict.get("Extracted Programming Languages", ""),  # 'llm extracted Programming Languages': 'I',
            vacancy_dict.get("Extracted Technologies", ""),  # 'llm extracted technologies': 'J',
            vacancy_dict.get("Extracted English Level", ""),  # 'llm extracted English Level': 'K',
            vacancy_dict.get("Extracted Rate", ""),  # 'llm extracted Rate': 'L',
            vacancy_dict.get("Extracted Expertise", ""),  # 'llm extracted expertise': 'M',
            vacancy_dict.get("Extracted Industry", ""),  # 'llm extracted industry': 'N',
            vacancy_dict.get("Extracted Location", ""),  # 'llm extracted location': 'O',
            vacancy_dict.get("Selected Candidates", ""),  # 'llm selected candidates': 'P',
            vacancy_dict.get("Reasoning", ""),  # 'reasoning': 'Q',
            vacancy_dict.get("step1_candidates_number", ""),  # 'step1 num number of initial candidates': 'R',
            vacancy_dict.get("technologies_coverage", ""),  # 'technologies_coverage': 'S',
            vacancy_dict.get("step3_candidates_number", ""),  # 'step3 num number of filtered candidates': 'T',
            vacancy_dict.get("step4_candidates_number", ""),  # 'step4 num number of llm selected candidates': 'U',
            user,  # 'user': 'V',
            vacancy_dict.get("list_of_filtered_candidates", ""),  # 'list of filtered candidates': 'W'
            f"{vacancy_dict.get('step0_time', 0):.1f} sec",  # 'step0_time': 'X',
            f"{vacancy_dict.get('step1_time', 0):.1f} sec",  # 'step1_time': 'Y',
            f"{vacancy_dict.get('step2_time', 0):.1f} sec",  # 'step2_time': 'Z',
            f"{vacancy_dict.get('step3_time', 0):.1f} sec",  # 'step3_time': 'AA',
            f"{vacancy_dict.get('step4_time', 0):.1f} sec",  # 'step4_time': 'AB',
            f"{vacancy_dict.get('step5_time', 0):.1f} sec",  # 'step5_time': 'AC',
            f"{vacancy_dict.get('total_time', 0):.1f} sec",  # 'total_time': 'AD'
            vacancy_dict.get("Model Used vacancy_details", ""),  # 'Model Used vacancy_details': 'AE'
            vacancy_dict.get("Cost vacancy_details", 0),  # 'Cost vacancy_details': 'AF'
            vacancy_dict.get("Model Used vacancy_industry", ""),  # 'Model Used vacancy_industry': 'AG'
            vacancy_dict.get("Cost vacancy_industry", 0),  # 'Cost vacancy_industry': 'AH'
            vacancy_dict.get("Model Used vacancy_location", ""),  # 'Model Used vacancy_location': 'AI'
            vacancy_dict.get("Cost vacancy_location", 0),  # 'Cost vacancy_location': 'AJ'
            vacancy_dict.get("Model Used candidates_selection", ""),  # 'Model Used candidates_selection': 'AK'
            vacancy_dict.get("Cost candidates_selection", 0),  # 'Cost candidates_selection': 'AL'
            total_cost  # 'Total Cost': 'AM'
        ]

        value_range_body = {
            "majorDimension": "ROWS",
            "values": [results],
        }

        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=range_db,
            valueInputOption=value_input_option,
            body=value_range_body
        ).execute()

        logger.info("Results saved to Google Sheets.")

    except HttpError as err:
        logger.error(f"An error occurred: {err}")
