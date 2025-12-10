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


SERVICE_ACCOUNT_JSON_PATH = os.getenv('SERVICE_ACCOUNT_JSON_PATH')
CANDIDATES_SHEET_NAME = os.getenv('CANDIDATES_SHEET_NAME')
CANDIDATES_SHEET_ID = os.getenv('CANDIDATES_SHEET_ID')
VACANCIES_SHEET_NAME = os.getenv('VACANCIES_SHEET_NAME')
VACANCIES_SHEET_ID = os.getenv('VACANCIES_SHEET_ID')

# Dictionary mapping sheet names to column names and their letter indices
sheets_columns_dict = {
   'Cash Search': {
        'Date': 'A',
        'vacancy description': 'B',
        'tg_answer': 'C',
        'step1 num number of initial candidates': 'D'
    }
}

def get_sheet_dict(sheet_name, sheet=None, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
    """
    Returns a dictionary mapping column names to their letter designations for the specified sheet.
    If the sheet is not found in the cache, loads the headers from Google Sheets.
    Args:
        sheet_name (str): Sheet name
        sheet: service.spreadsheets() object (will be initialized if None)
    Returns:
        dict: A dictionary mapping column names to their letter designations
    """
    if sheet_name in sheets_columns_dict:
        return sheets_columns_dict[sheet_name]
    spreadsheet_id = os.getenv(spreadsheet_env_name)

    logger.info(f"Лист '{sheet_name}' не найден в кэше, загружаем заголовки из Google Sheets...")
    if sheet is None:
        service = initialize_google_sheets_api()
        sheet = service.spreadsheets()

    range_name = f"{sheet_name}!1:1"
    response = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    header_row = response.get('values', [])[0]
    sheet_dict = {col.strip(): index_to_letter(i) for i, col in enumerate(header_row)}
    sheets_columns_dict[sheet_name] = sheet_dict
    return sheet_dict


def get_column_letters(columns, sheet_name, ignore_missing=False, sheet=None, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
    """
    Returns the column abbreviations for the specified column names from the specified sheet.
    Args:
        columns (str or list): The name(s) of the columns to retrieve the abbreviations for
        sheet_name (str): The sheet name
        ignore_missing (bool): If True, skips missing columns instead of raising an error
        sheet: The service.spreadsheets() object (will be initialized if None)
    Returns:
        str or list: Column abbreviations
    Raises:
        ValueError: If the column name is not found (if ignore_missing=False)
    """
    sheet_dict = get_sheet_dict(sheet_name, sheet, spreadsheet_env_name=spreadsheet_env_name)
    if isinstance(columns, str):
        col = columns
        if col not in sheet_dict:
            if ignore_missing:
                return None
            raise ValueError(
                f"Колонка '{col}' не найдена на листе '{sheet_name}'. Доступные колонки: {list(sheet_dict.keys())}")
        return sheet_dict[col]
    elif isinstance(columns, list):
        result = []
        for col in columns:
            if col not in sheet_dict:
                if ignore_missing:
                    continue
                raise ValueError(
                    f"Колонка '{col}' не найдена на листе '{sheet_name}'. Доступные колонки: {list(sheet_dict.keys())}")
            result.append(sheet_dict[col])
        return result
    else:
        raise ValueError("Параметр columns функции get_column_letters() должен быть строкой или списком строк.")


# Authenticate with credentials.json
def initialize_google_sheets_api():
    """
    Initializes and returns the Google Sheets API service.
    """
    credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_JSON_PATH,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
    return build('sheets', 'v4', credentials=credentials)

def remove_extra_spaces_from_headers(service=None, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
    # Initialize Google Sheets API if service is not provided
    if service is None:
        service = initialize_google_sheets_api()

    spreadsheet_id = os.getenv(spreadsheet_env_name)

    sheet = service.spreadsheets()

    # get first row from the sheet (headers)
    range_name = f"{CANDIDATES_SHEET_NAME}!1:1"
    response = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    header_row = response.get('values', [])[0]

    # remove extra spaces from headers
    stripped_header_row = [col.strip() for col in header_row]

    # updating first row in the sheet
    update_body = {
        'values': [stripped_header_row]
    }
    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption='RAW',
        body=update_body
    ).execute()

def letter_to_index(col_letter):
    index = 0
    for char in col_letter:
        index = index * 26 + (ord(char.upper()) - ord('A')) + 1
    return index - 1

def index_to_letter(col_index: int) -> str:
    letters = []
    while col_index >= 0:
        letters.append(chr(ord('A') + col_index % 26))
        col_index = col_index // 26 - 1
    return ''.join(reversed(letters))


def remove_invisible_chars(text, remove_emonji=False):
    if remove_emonji:
        pattern = r'[^\w\s&.,\-()]'
    else:
        pattern = r'[\x00-\x09\x0B-\x1F\x7F-\x9F]'
    visible_text = re.sub(pattern, '', text)
    return visible_text.strip()

def read_specific_columns(columns_to_extract, sheet_name=CANDIDATES_SHEET_NAME, service=None, remove_emonji=False, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
    """
    Fetches specific columns from the Google Sheet, handling hyperlinks.
    Creates missing columns and fills them with empty strings.
    Returns a DataFrame.
    """

    # Initialize Google Sheets API if service is not provided
    if service is None:
        service = initialize_google_sheets_api()

    spreadsheet_id = os.getenv(spreadsheet_env_name)

    sheet = service.spreadsheets()
    # Convert column names to letters
    columns_letters = get_column_letters(columns_to_extract, sheet_name, sheet=sheet, spreadsheet_env_name=spreadsheet_env_name)

    # Get the full sheet data with includeGridData
    spreadsheet = sheet.get(spreadsheetId=spreadsheet_id, ranges=[sheet_name], includeGridData=True).execute()
    sheet_data = spreadsheet['sheets'][0]['data'][0]

    # Extract headers from the sheet
    headers_row = sheet_data.get('rowData', [{}])[0].get('values', [])
    headers = [cell.get('formattedValue', '').strip() for cell in headers_row]

    # Check if the headers match the expected column names
    for i, column_name in enumerate(columns_to_extract):
        column_letter = get_column_letters(column_name, sheet_name, sheet=sheet)
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
                    cell_text = remove_invisible_chars(cell_text, remove_emonji)
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

def write_specific_columns(
    df,
    sheet_name=CANDIDATES_SHEET_NAME,
    service=None,
    rows_to_highlight=None,
    highlight_color=None,
        spreadsheet_env_name='STAFF_SPREADSHEET_ID'
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

    spreadsheet_id = os.getenv(spreadsheet_env_name)

    sheet = service.spreadsheets()

    # Set default highlight color if not provided
    if highlight_color is None:
        highlight_color = {'red': 1.0, 'green': 1.0, 'blue': 0.0}

    # Update each column
    for column_name in df.columns:
        column_letter = get_column_letters(column_name, sheet_name, sheet=sheet)
        if column_letter is None:
            raise ValueError(f"Column name '{column_name}' is invalid or not mapped in column_dict.")

        # Update header
        header_range = f"{sheet_name}!{column_letter}1"
        header_update_body = {'values': [[column_name]]}
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueInputOption='RAW',
            body=header_update_body
        ).execute()

        # Update data
        values = df[column_name].fillna('').astype(str).tolist()
        range_to_update = f"{sheet_name}!{column_letter}2:{column_letter}{len(df) + 1}"
        update_body = {'values': [[value] for value in values]}
        sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_to_update,
            valueInputOption='RAW',
            body=update_body
        ).execute()

    # Highlight rows if requested
    if rows_to_highlight:
        requests = []
        for row in rows_to_highlight:
            for column_name in df.columns:
                column_letter = get_column_letters(column_name, sheet_name, sheet=sheet)
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
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

def get_spreadsheet_id(sheet_name, sheet=None, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
    """
    Returns the sheetId for a given sheet name in the spreadsheet.
    Args:
        sheet_name (str): Name of the sheet
        sheet: Google Sheets API spreadsheets() object (will be initialized if None)
    Returns:
        int: sheetId
    Raises:
        ValueError: If sheet_name not found in the spreadsheet
    """
    try:
        spreadsheet_id = os.getenv(spreadsheet_env_name)
            
        if sheet is None:
            service = initialize_google_sheets_api()
            sheet = service.spreadsheets()
        spreadsheet_metadata = sheet.get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId,title))"
        ).execute()
        sheets = spreadsheet_metadata.get('sheets', [])
        target_sheet = next((s for s in sheets if s['properties']['title'] == sheet_name), None)
        if not target_sheet:
            raise ValueError(f"Sheet '{sheet_name}' not found in the spreadsheet.")
        return target_sheet['properties']['sheetId']
    except Exception as e:
        logger.error(f"Error getting sheetId for '{sheet_name}': {str(e)}")
        raise e


def _prepare_cell_value(value):
    if value is None:
        return ''
    # List or tuple of STRINGS
    if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
        if any(len(x) > 22 for x in value):
            return "\n\n".join(value)
        return ", ".join(value)
    # Other types
    return str(value)


def write_dict_to_sheet(data_dict, sheet_name, service=None, row_number=None, spreadsheet_env_name='STAFF_SPREADSHEET_ID'):
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

        spreadsheet_id = os.getenv(spreadsheet_env_name)

        sheet = service.spreadsheets()

        # Get the sheet columns dictionary
        sheet_dict = get_sheet_dict(sheet_name, sheet, spreadsheet_env_name)

        # Filter data_dict to only include keys that exist as columns
        filtered_data = {key: value for key, value in data_dict.items() if key in sheet_dict}
        if not filtered_data:
            logger.warning(f"No matching columns found for provided data keys: {list(data_dict.keys())}")
            return None

        gid = get_spreadsheet_id(sheet_name, sheet, spreadsheet_env_name)
        # If no row_number specified, insert new row at position 2
        if row_number is None:
            # Insert a new row at position 2 (after headers)
            insert_request = {
                'insertDimension': {
                    'range': {
                        'sheetId': gid,
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
                spreadsheetId=spreadsheet_id,
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
                'values': [[_prepare_cell_value(value)]]
            })

        # Batch update all cells
        if updates:
            batch_update_data = {
                'valueInputOption': 'USER_ENTERED',  # Allows formulas and formatting
                'data': updates
            }

            response = sheet.values().batchUpdate(
                spreadsheetId=spreadsheet_id,
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


def write_value_to_cell(
    value,
    sheet_name,
    cell_range,
    service=None,
    spreadsheet_env_name='STAFF_SPREADSHEET_ID'
) -> dict:
    """
    Записывает значение в указанную ячейку Google Sheets.

    Args:
        value: Значение для записи (строка, число, формула и т.д.).
        sheet_name (str): Название листа.
        cell_range (str): Адрес ячейки (например, "A1", "B2", "C3").
        service: Объект Google Sheets API (если не передан, будет инициализирован).
        spreadsheet_env_name (str): Название переменной окружения с идентификатором документа.

    Returns:
        dict: Ответ от Google Sheets API.
    """
    try:
        if service is None:
            service = initialize_google_sheets_api()

        spreadsheet_id = os.getenv(spreadsheet_env_name)
        sheet = service.spreadsheets()

        # Формируем диапазон для обновления (например, "Cash Search!A1")
        full_range = f"{sheet_name}!{cell_range}"

        # Подготавливаем тело запроса
        update_body = {
            'values': [[value]]
        }

        # Обновляем значение в ячейке
        response = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption='USER_ENTERED',  # Позволяет записывать формулы и форматированные значения
            body=update_body
        ).execute()

        logger.info(f"Successfully wrote value '{value}' to cell {full_range}")
        return response

    except Exception as e:
        logger.error(f"Error writing to cell {full_range}: {str(e)}")
        raise e

def write_value_to_cell(
    value,
    sheet_name: str,
    cell_range: str,
    service=None,
    spreadsheet_env_name: str = 'STAFF_SPREADSHEET_ID'
) -> None:
    """
    Writes a single value to a specific cell in a Google Sheet.
    Args:
        value: The value to write (string, number, formula, etc.).
        sheet_name: Name of the sheet (e.g., "Cash Search").
        cell_range: Cell address (e.g., "A1", "B2").
        service: Google Sheets API service object (initialized if None).
        spreadsheet_env_name: Environment variable name for the spreadsheet ID.
    Returns:
        dict: Response from the Google Sheets API.
    Raises:
        Exception: If an error occurs during the API call.
    """
    try:
        # Initialize Google Sheets API if service is not provided
        if service is None:
            service = initialize_google_sheets_api()
        # Get the spreadsheet ID from environment variables
        spreadsheet_id = os.getenv(spreadsheet_env_name)
        sheet = service.spreadsheets()
        # Format the full range (e.g., "Cash Search!A1")
        full_range = f"{sheet_name}!{cell_range}"
        # Prepare the request body
        update_body = {'values': [[value]]}
        # Update the cell value
        response = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=full_range,
            valueInputOption='USER_ENTERED',  # Allows formulas and formatted values
            body=update_body
        ).execute()
        logger.info(f"Successfully wrote value '{value}' to cell {full_range}")
    except Exception as e:
        logger.error(f"Error writing to cell {full_range}: {str(e)}")
        raise e

