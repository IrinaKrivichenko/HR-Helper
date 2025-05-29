
import os
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from src.data_processing.jaccard_similarity import calculate_jaccard_similarity
from src.google_services.sheets import read_specific_columns, initialize_google_sheets_api
from src.logger import logger
from src.nlp.tokenization import get_tokens

load_dotenv()

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
                          "number of initial candidates", "user"]

    # Read specific columns from the vacancies sheet
    vacancies_df = read_specific_columns(columns_to_extract, os.getenv("VACANCIES_SHEET_NAME"))

    # Convert the input vacancy description to a set of words
    input_word_set = get_tokens(vacancy_description)

    # Check each row for a similar vacancy
    for index, row in vacancies_df.iterrows():
        saved_date_str = row['Date']
        saved_date = datetime.strptime(saved_date_str, '%Y-%m-%d')

        # Check if the date is within the last VACANCY_CACHE_TIME days
        if saved_date < some_days_ago:
            break

        saved_description = row['vacancy description']

        # Convert the saved vacancy description to a set of words
        saved_word_set = get_tokens(saved_description)
        jaccard_similarity = calculate_jaccard_similarity(input_word_set, saved_word_set)
        # Check if the descriptions are similar
        if jaccard_similarity >= 0.95:
            return row
        if jaccard_similarity >= 0.8:
            del row['first_answer']
            return row  # Return the row index and the user

    return None

def save_vacancy_description(vacancy_description,
                             existing_vacancy,
                             llm_extracted_data,
                             final_answer,
                             user,
                             num_initial_candidates,
                             consign_similarity_threshold,
                             num_filtered_candidates,
                             num_llm_selected_candidates,
                             list_of_filtered_candidated,
                             time_taken,
                             service=None):
    """
    Saves the vacancy description and related data to Google Sheets.
    """
    # Initialize the Google Sheets API
    if service is None:
        service = initialize_google_sheets_api()
    try:
        SHEET_ID = os.getenv("SHEET_ID")
        VACANCIES_SHEET_NAME = os.getenv("VACANCIES_SHEET_NAME")
        VACANCIES_SHEET_ID = os.getenv("VACANCIES_SHEET_ID")
        if existing_vacancy is not None:
            # If a similar vacancy exists, unpack the result and update the existing row
            row_index = existing_vacancy['Row in Spreadsheets']  #['row']
            range_db = f"{VACANCIES_SHEET_NAME}!A{row_index}:R{row_index}"
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
            range_db = f"{VACANCIES_SHEET_NAME}!A2:R2"

        value_input_option = "RAW"
        current_date = datetime.now().strftime('%Y-%m-%d')
        results = [
            current_date,  #   'Date': 'A',
            llm_extracted_data.get("error_logs", ""),  #   'llm errors': 'B',
            vacancy_description,  #   'vacancy description': 'C',
            final_answer,  #   'first_answer': 'D',
            llm_extracted_data.get("Extracted Role", ""),  #   'llm extracted role': 'E',
            llm_extracted_data.get("Extracted Technologies", ""),  #   'llm extracted technologies': 'F',
            llm_extracted_data.get("Extracted Industry", ""),  #   'llm extracted industry': 'G',
            llm_extracted_data.get("Extracted Expertise", ""),  #   'llm extracted expertise': 'H',
            llm_extracted_data.get("Extracted Location", ""),  #   'llm extracted location': 'I',
            llm_extracted_data.get("Selected Candidates", ""),  #   'llm selected candidates': 'J',
            llm_extracted_data.get("Reasoning", ""),   #   'reasoning': 'K',
            num_initial_candidates,  #   'number of initial candidates': 'L',
            consign_similarity_threshold,  #   'consign similarity threshold': 'M',
            num_filtered_candidates,  #   'number of filtered candidates': 'N',
            num_llm_selected_candidates,  #   'number of llm selected candidates': 'O',
            user,  #   'user': 'P',
            list_of_filtered_candidated,  #   'list of filtered candidated': 'Q'
            f"{time_taken:.1f} seconds"
        ]

        # This is the 'value_range_body' or JSON
        value_range_body = {
            "majorDimension": "ROWS",
            "values": [results],
        }

        # Insert or update the data into the specified range
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=range_db,
            valueInputOption=value_input_option,
            body=value_range_body
        ).execute()

        logger.info("Results saved to Google Sheets.")

    except HttpError as err:
        logger.error(f"An error occurred: {err}")
