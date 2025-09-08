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

# Dictionary mapping sheet names to column names and their letter indices
sheets_columns_dict = {
    'staff': {
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
        '№': 'AC',
        'Date of CV': 'AD',
        'GitHub': 'AE',
        'Embedding': 'BA',
        'Role_Embedding': 'BB',
        'Industry_Embedding': 'BC',
    },

    'values': {
        'From Values': 'A',
        'LVL of engagement Values': 'B',
        'Seniority Values': 'C',
        'Role Values': 'D',
        'Industry Values': 'E',
    },

    'Cash': {
        'Date': 'A',
        'vacancy description': 'B',
        'first_answer': 'C',
        'step1 num number of initial candidates': 'D'
    }
}

def get_column_letters(columns, sheet_name, ignore_missing=False):
    """
    Returns the column letters for the given column names from a specific sheet.

    Args:
        sheet_name (str): Name of the sheet ('staff', 'values', 'cash')
        columns (str or list): Column name(s) to get letters for
        ignore_missing (bool): If True, skip missing columns instead of raising error

    Returns:
        str or list: Column letter(s) corresponding to the column name(s)

    Raises:
        ValueError: If sheet_name doesn't exist or column name not found (when ignore_missing=False)
    """
    try:
        # Check if sheet exists
        if sheet_name not in sheets_columns_dict:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {list(sheets_columns_dict.keys())}")

        sheet_dict = sheets_columns_dict[sheet_name]

        if isinstance(columns, str):
            col = columns
            if col not in sheet_dict:
                if ignore_missing:
                    return None
                raise ValueError(
                    f"Column '{col}' not found in sheet '{sheet_name}'. Available columns: {list(sheet_dict.keys())}")
            return sheet_dict[col]

        elif isinstance(columns, list):
            result = []
            for col in columns:
                if col not in sheet_dict:
                    if ignore_missing:
                        continue
                    raise ValueError(
                        f"Column '{col}' not found in sheet '{sheet_name}'. Available columns: {list(sheet_dict.keys())}")
                result.append(sheet_dict[col])
            return result

        else:
            raise ValueError("get_column_letters() columns parameter should be a string or a list of strings.")

    except Exception as e:
        raise e


# Authenticate with credentials.json

SERVICE_ACCOUNT_JSON_PATH = os.getenv('SERVICE_ACCOUNT_JSON_PATH')
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
                SERVICE_ACCOUNT_JSON_PATH,
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
    visible_text = re.sub(r'[\x00-\x09\x0B-\x1F\x7F-\x9F]', '', text)
    return visible_text

def read_specific_columns(columns_to_extract, sheet_name=CANDIDATES_SHEET_NAME, service=None):
    """
    Fetches specific columns from the Google Sheet, handling hyperlinks.
    Creates missing columns and fills them with empty strings.
    Returns a DataFrame.
    """
    # Convert column names to letters
    columns_letters = get_column_letters(columns_to_extract, sheet_name)

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
        column_letter = get_column_letters(column_name, sheet_name)
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
#     columns_to_extract = get_column_letters(columns_to_extract, sheet_name)
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

def write_specific_columns(
    df,
    sheet_name=CANDIDATES_SHEET_NAME,
    service=None,
    rows_to_highlight=None,
    highlight_color=None
):
    """
    Writes each column from a DataFrame back to the Google Sheet according to the specified column letters.
    Optionally highlights specified rows with a background color.

    Args:
    - df (pd.DataFrame): DataFrame containing the data to write.
    - rows_to_highlight (list): List of row indices (0-based) to highlight.
    - highlight_color (dict): Color in RGB format, e.g., {'red': 1.0, 'green': 0.9, 'blue': 0.9}.
    """
    if service is None:
        service = initialize_google_sheets_api()
    sheet = service.spreadsheets()

    # Set default highlight color if not provided
    if highlight_color is None:
        highlight_color = {'red': 1.0, 'green': 1.0, 'blue': 0.0}

    # Update each column
    for column_name in df.columns:
        column_letter = get_column_letters(column_name)
        if column_letter is None:
            raise ValueError(f"Column name '{column_name}' is invalid or not mapped in column_dict.")

        # Update header
        header_range = f"{sheet_name}!{column_letter}1"
        header_update_body = {'values': [[column_name]]}
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=header_range,
            valueInputOption='RAW',
            body=header_update_body
        ).execute()

        # Update data
        values = df[column_name].fillna('').astype(str).tolist()
        range_to_update = f"{sheet_name}!{column_letter}2:{column_letter}{len(df) + 1}"
        update_body = {'values': [[value] for value in values]}
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=range_to_update,
            valueInputOption='RAW',
            body=update_body
        ).execute()

    # Highlight rows if requested
    if rows_to_highlight:
        requests = []
        for row in rows_to_highlight:
            for column_name in df.columns:
                column_letter = get_column_letters(column_name)
                cell_range = f"{sheet_name}!{column_letter}{row + 2}"  # +2 because data starts at row 2
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,  # Assuming the first sheet
                            "startRowIndex": row + 1,  # +1 because headers are in row 0
                            "endRowIndex": row + 2,
                            "startColumnIndex": ord(column_letter) - ord('A'),
                            "endColumnIndex": ord(column_letter) - ord('A') + 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": highlight_color
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })

        # Apply formatting
        body = {'requests': requests}
        sheet.batchUpdate(
            spreadsheetId=SHEET_ID,
            body=body
        ).execute()

def write_dict_to_sheet(data_dict, sheet_name, service=None, row_number=None):
    """
    Writes dictionary data to a Google Sheet row, matching keys to column names.

    Args:
        data_dict (dict): Dictionary with data to write (keys should match column names)
        sheet_name (str): Name of the sheet ('staff', 'values', 'cash')
        service: Google Sheets API service object (will be initialized if None)
        row_number (int, optional): Specific row number to write to. If None, inserts new row at position 2

    Returns:
        dict: Response from Google Sheets API

    Raises:
        ValueError: If sheet_name doesn't exist
    """
    try:
        # Initialize Google Sheets API if service is not provided
        if service is None:
            service = initialize_google_sheets_api()

        # Check if sheet exists
        if sheet_name not in sheets_columns_dict:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {list(sheets_columns_dict.keys())}")

        sheet = service.spreadsheets()

        # Get sheet columns dictionary
        sheet_dict = sheets_columns_dict[sheet_name]

        # Filter data_dict to only include keys that exist as columns
        filtered_data = {key: value for key, value in data_dict.items() if key in sheet_dict}

        if not filtered_data:
            logger.warning(f"No matching columns found for provided data keys: {list(data_dict.keys())}")
            return None

        # If no row_number specified, insert new row at position 2
        if row_number is None:
            # Insert a new row at position 2 (after headers)
            insert_request = {
                'insertDimension': {
                    'range': {
                        'sheetId': globals().get(f'{sheet_name.upper()}_SHEET_ID') or 0,  # fallback to 0 if not found
                        'dimension': 'ROWS',
                        'startIndex': 1,  # Insert after row 1 (headers)
                        'endIndex': 2
                    },
                    'inheritFromBefore': False
                }
            }

            batch_update_request = {
                'requests': [insert_request]
            }

            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body=batch_update_request
            ).execute()

            row_number = 2  # Use the newly inserted row

        # Prepare updates for each column
        updates = []
        for column_name, value in filtered_data.items():
            column_letter = sheet_dict[column_name]
            cell_range = f"{sheet_name}!{column_letter}{row_number}"

            updates.append({
                'range': cell_range,
                'values': [[str(value) if value is not None else '']]
            })

        # Batch update all cells
        if updates:
            batch_update_data = {
                'valueInputOption': 'USER_ENTERED',  # Allows formulas and formatting
                'data': updates
            }

            response = sheet.values().batchUpdate(
                spreadsheetId=SHEET_ID,
                body=batch_update_data
            ).execute()

            logger.info(f"Successfully wrote {len(filtered_data)} fields to {sheet_name} row {row_number}")
            logger.info(f"Written fields: {list(filtered_data.keys())}")

            # Log ignored fields if any
            ignored_fields = set(data_dict.keys()) - set(filtered_data.keys())
            if ignored_fields:
                logger.info(f"Ignored fields (no matching columns): {list(ignored_fields)}")

            return response

    except Exception as e:
        logger.error(f"Error writing to sheet {sheet_name}: {str(e)}")
        raise e
