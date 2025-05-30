import re
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request


import os
from dotenv import load_dotenv

from src.logger import logger

load_dotenv()

# Dictionary mapping column names to their letter indices
column_dict = {
    # c2b
    'First Name': 'A', 'Last Name': 'B',
    'From': 'C',
    'LVL of engagement': 'D',
    'Seniority': 'E', 'Role': 'F',
    'LinkedIn': 'G', 'Telegram': 'H', 'Phone': 'I', 'Email': 'J',
    'Stack': 'K', 'Industry': 'L', 'Expertise': 'M',
    'Belarusian': 'N', 'English': 'O',
    'Works hrs/mnth': 'P',
    'Location': 'Q',
    'CV (original)': 'R', 'CV White Label': 'S',
    'Folder': 'T',
    'Entry wage rate (EWR)': 'U', 'EWR 168hr/mnth': 'V',
    'Preferred wage rate (PWR)': 'W', 'PWR 168hr/mnth': 'X',
    'Sell rate': 'Y',
    "Legal entity we'll pay to": 'Z',
    'NDA': 'AA',
    'Comment': 'AB',
    'Embedding': 'BA',
    'Role_Embedding': 'BB',
    'Stack_Embedding': 'BC',
    '': 'BD',

    # vacancies
    'Date': 'A',
    'llm errors': 'B',
    'vacancy description': 'C',
    'first_answer': 'D',
    'llm extracted role': 'E',
    'llm extracted technologies': 'F',
    'llm extracted industry': 'G',
    'llm extracted expertise': 'H',
    'llm extracted location': 'I',
    'llm selected candidates': 'J',
    'reasoning': 'K',
    'number of initial candidates': 'L',
    'consign similarity threshold': 'M',
    'number of filtered candidates': 'N',
    'number of llm selected candidates': 'O',
    'user': 'P',
    'list of filtered candidated': 'Q',
    'time taken to process the vacancy': 'R'
}


def get_column_letters(columns):
    """
    Returns the column letters for the given column names.
    Handles both single column names and lists of column names.
    """
    try:
      if isinstance(columns, str):
          col = columns
          return column_dict[col]
      elif isinstance(columns, list):
          return [column_dict[col] for col in columns]
      else:
          raise ValueError("get_column_letters() input should be a string or a list of strings.")
    except KeyError:
        raise ValueError(f"There is no column named {col}")


# Authenticate with credentials.json

CREDS_JSON_PATH = "configs/ostlab-hr-b79582d6308b.json"
SHEET_ID = os.getenv('SHEET_ID')
CANDIDATES_SHEET_NAME = os.getenv('CANDIDATES_SHEET_NAME')
CANDIDATES_SHEET_ID = os.getenv('CANDIDATES_SHEET_ID')
VACANCIES_SHEET_NAME = os.getenv('VACANCIES_SHEET_NAME')
VACANCIES_SHEET_ID = os.getenv('VACANCIES_SHEET_ID')

def initialize_google_sheets_api():
    """
    Initializes and returns the Google Sheets API service.
    """
    credentials = service_account.Credentials.from_service_account_file(
                CREDS_JSON_PATH,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
    return build('sheets', 'v4', credentials=credentials)

def remove_extra_spaces_from_headers(service=None):
    # Initialize Google Sheets API if service is not provided
    if service is None:
        service = initialize_google_sheets_api()
    sheet = service.spreadsheets()

    # get first row from the sheet (headers)
    range_name = f"{CANDIDATES_SHEET_NAME}!1:1"
    response = sheet.values().get(spreadsheetId=SHEET_ID, range=range_name).execute()
    header_row = response.get('values', [])[0]

    # remove extra spaces from headers
    stripped_header_row = [col.strip() for col in header_row]

    # updating first row in the sheet
    update_body = {
        'values': [stripped_header_row]
    }
    sheet.values().update(
        spreadsheetId=SHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        body=update_body
    ).execute()

def letter_to_index(col_letter):
    index = 0
    for char in col_letter:
        index = index * 26 + (ord(char.upper()) - ord('A')) + 1
    return index - 1

def remove_invisible_chars(text):
    visible_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    return visible_text

def read_specific_columns(columns_to_extract, sheet_name=CANDIDATES_SHEET_NAME, service=None):
    """
    Fetches specific columns from the Google Sheet, handling hyperlinks.
    Creates missing columns and fills them with empty strings.
    Returns a DataFrame.
    """
    # Convert column names to letters
    columns_letters = get_column_letters(columns_to_extract)

    # Initialize Google Sheets API if service is not provided
    if service is None:
        service = initialize_google_sheets_api()
    sheet = service.spreadsheets()

    # Get the full sheet data with includeGridData
    spreadsheet = sheet.get(spreadsheetId=SHEET_ID, ranges=[sheet_name], includeGridData=True).execute()
    sheet_data = spreadsheet['sheets'][0]['data'][0]

    # Extract headers from the sheet
    headers_row = sheet_data.get('rowData', [{}])[0].get('values', [])
    headers = [cell.get('formattedValue', '').strip() for cell in headers_row]

    # Check if the headers match the expected column names
    for i, column_name in enumerate(columns_to_extract):
        column_letter = get_column_letters(column_name)
        i = letter_to_index(column_letter)
        if i < len(headers) and headers[i] != column_name:
            logger.error(f"Column name mismatch at column {column_letter}: Expected '{column_name}', found '{headers[i]}'")

    # Extract values and hyperlinks for specific columns
    data = []
    rows = sheet_data.get('rowData', [])
    for row in rows:
        row_values = row.get('values', [])
        row_data = []
        for col_letter in columns_letters:
            col_index = letter_to_index(col_letter)
            if col_index is not None and col_index < len(row_values):
                cell = row_values[col_index]
                if 'hyperlink' in cell:
                    # If there is a hyperlink, add the URL
                    row_data.append(cell['hyperlink'])
                else:
                    # Otherwise, add the cell text
                    cell_text = cell.get('formattedValue', '') if 'formattedValue' in cell else ''
                    cell_text = cell_text.strip()
                    cell_text = remove_invisible_chars(cell_text)
                    row_data.append(cell_text)
            else:
                # If the column index is out of range or None, add an empty value
                row_data.append('')

        # Check if the row contains only empty strings
        if not all(value == '' for value in row_data):
            data.append(row_data)
        else:
            break  # Exit the loop if the row is completely empty

    # Create DataFrame with specific columns
    df = pd.DataFrame(data[1:], columns=columns_to_extract)
    df = df.reset_index(drop=True)
    df['Row in Spreadsheets'] = df.index + 2
    return df
#
# def read_specific_columns(columns_to_extract, sheet_name=CANDIDATES_SHEET_NAME, service=None):
#     """
#     Fetches specific columns from the Google Sheet, handling hyperlinks.
#     Creates missing columns and fills them with empty strings.
#     Returns a DataFrame.
#     """
#     # Convert column names to letters
#     columns_to_extract = get_column_letters(columns_to_extract)
#
#     # Initialize Google Sheets API if service is not provided
#     if service is None:
#         service = initialize_google_sheets_api()
#     sheet = service.spreadsheets()
#
#     # Get the full sheet data with includeGridData
#     spreadsheet = sheet.get(spreadsheetId=SHEET_ID, ranges=[sheet_name], includeGridData=True).execute()
#     sheet_data = spreadsheet['sheets'][0]['data'][0]
#
#     # Extract values and hyperlinks for specific columns
#     data = []
#     rows = sheet_data.get('rowData', [])
#     for row in rows:
#         row_values = row.get('values', [])
#         row_data = []
#         for col_letter in columns_to_extract:
#             col_index = letter_to_index(col_letter)
#             if col_index is not None and col_index < len(row_values):
#                 cell = row_values[col_index]
#                 if 'hyperlink' in cell:
#                     # If there is a hyperlink, add the URL
#                     row_data.append(cell['hyperlink'])
#                 else:
#                     # Otherwise, add the cell text
#                     cell_text = cell.get('formattedValue', '') if 'formattedValue' in cell else ''
#                     cell_text = cell_text.strip()
#                     cell_text = remove_invisible_chars(cell_text)
#                     row_data.append(cell_text)
#
#             else:
#                 # If the column index is out of range or None, add an empty value
#                 row_data.append('')
#
#         # Check if the row contains only empty strings
#         if not all(value == '' for value in row_data):
#             data.append(row_data)
#         else:
#             break  # Exit the loop if the row is completely empty
#
#     # Create DataFrame with specific columns
#     df = pd.DataFrame(data[1:], columns=data[0])
#     df = df.reset_index(drop=True)
#     df['Row in Spreadsheets'] = df.index + 2
#     return df

def write_specific_columns(df, sheet_name=CANDIDATES_SHEET_NAME, service=None):
    """
    Writes each column from a DataFrame back to the Google Sheet according to the specified column letters.
    Converts all values to strings before writing.

    Args:
    - df (pd.DataFrame): DataFrame containing the data to write.
    """
    # Initialize Google Sheets API
    if service is None:
        service = initialize_google_sheets_api()
    sheet = service.spreadsheets()

    # Iterate over each column in the DataFrame
    for column_name in df.columns:
        # Get the column letter from column_dict
        column_letter = get_column_letters(column_name)
        if column_letter is None:
            raise ValueError(f"Column name '{column_name}' is invalid or not mapped in column_dict.")

        # Update the header (column name) in the first row
        header_range = f"{sheet_name}!{column_letter}1"
        header_update_body = {
            'values': [[column_name]]
        }
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=header_range,
            valueInputOption='RAW',
            body=header_update_body
        ).execute()

        # Prepare the data to write for the current column, converting all values to strings
        values = df[column_name].fillna('').astype(str).tolist()

        # Define the range to update (assuming the data starts from the second row)
        range_to_update = f"{sheet_name}!{column_letter}2:{column_letter}{len(df) + 1}"

        # Create the update request body
        update_body = {
            'values': [[value] for value in values]  # Ensure values are in the correct format
        }

        # Update the sheet with the DataFrame data for the current column
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body=update_body
        ).execute()

