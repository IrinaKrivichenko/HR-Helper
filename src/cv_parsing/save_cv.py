import os
import re
from datetime import datetime

from dotenv import load_dotenv
from tzlocal import get_localzone

from src.google_services.drive import initialize_google_drive_api, check_or_create_subfolder, check_file_exists, \
    upload_file_to_drive, get_file_id, add_editor_to_file

load_dotenv()

from src.google_services.sheets import write_dict_to_sheet
from googleapiclient.http import MediaFileUpload


def save_cv_info(extracted_data, file_path):
    if file_path is not None:
        extracted_data, full_name, drive_file_name = check_the_original_file_name(extracted_data, file_path)
        if os.path.exists(file_path):
            existence_cv, extracted_data = save_cv_to_google_drive(extracted_data, file_path, full_name, drive_file_name)
        else:
            existence_cv = ""
    else:
        existence_cv = "you haven't send me file"
        full_name = f'{extracted_data["First Name"]} {extracted_data["Last Name"]}'.strip()
    extracted_data["№"] = "=A3+1"
    extracted_data["EWR 168hr/mnth"] = "=CEILING(Y2*168;10)"
    extracted_data["PWR 168hr/mnth"] = "=CEILING(AA2*168;10)"
    local_timezone = get_localzone()
    extracted_data["Date of CV parsing"] = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
    if  "Phone" in extracted_data and extracted_data["Phone"]:
        extracted_data["Phone"] = f"'{extracted_data['Phone']}"

    write_dict_to_sheet(data_dict=extracted_data, sheet_name="staff")
    keys = ""
    for key in extracted_data.keys():
        keys = f"{keys}\t{key}"
    print(keys)


    write_dict_to_sheet(data_dict=extracted_data, sheet_name=os.getenv("PARSE_LOGS_SHEET_NAME"))

    doc_id = os.getenv("SHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A2'>{full_name} {existence_cv}CV is parsed</a>"
    return google_sheet_row_link


def check_the_original_file_name(extracted_data, file_path):
    # 1. Check the original file name
    original_file_name = os.path.basename(file_path)
    file_name_without_ext = original_file_name.split(".")[0]
    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+CV\s+(.+?)(?:\s+(.+?))?$", file_name_without_ext)

    if match:
        # If the original file name matches the pattern, use it
        date_from_file, name_from_file, surname_from_file = match.groups()
        extracted_data["Date of CV"] = date_from_file
        extracted_data["First Name"] = name_from_file
        extracted_data["Last Name"] = surname_from_file or ""
        full_name = f"{name_from_file} {surname_from_file}".strip()
        drive_file_name = original_file_name  # Use the original file name
    else:
        # If not, generate a new file name
        name = extracted_data.get("First Name", "")
        surname = extracted_data.get("Last Name", "")
        full_name = f"{name} {surname}".strip()
        current_date = datetime.now().strftime('%Y-%m-%d')
        extracted_data["Date of CV"] = current_date
        drive_file_name = f"{current_date} CV {full_name}.{original_file_name.split('.')[-1]}"
    return extracted_data, full_name, drive_file_name

def save_cv_to_google_drive(extracted_data, file_path, full_name, drive_file_name):
    """
    Saves CV to Google Drive.
    Returns existence_cv: "", "new", or "existing".
    """
    # 1. Work with Google Drive
    service = initialize_google_drive_api()
    root_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    # Check or create candidate's subfolder
    subfolder_id = check_or_create_subfolder(root_folder_id, full_name, service)
    # Check if the file exists in the subfolder
    file_exists = check_file_exists(subfolder_id, drive_file_name, service)
    # Upload the file if it doesn't exist
    if not file_exists:
        file_id = upload_file_to_drive(file_path, subfolder_id, drive_file_name, service)
    else:
        file_id = get_file_id(subfolder_id, drive_file_name, service)

    # 2. Add editors to the file
    editors = os.getenv("GOOGLE_DRIVE_EDITORS", "").split(",")
    for editor in editors:
        if editor.strip():
            add_editor_to_file(file_id, editor.strip(), service)

    # 3. Generate links
    folder_link = f"https://drive.google.com/drive/folders/{subfolder_id}"
    file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    # 4. Update extracted_data with links
    extracted_data["Folder"] = folder_link
    extracted_data["CV (original)"] = file_link

    # 5. Set existence_cv
    if not file_exists:
        existence_cv = "new " if subfolder_id else ""
    else:
        existence_cv = "existing "

    return existence_cv, extracted_data
