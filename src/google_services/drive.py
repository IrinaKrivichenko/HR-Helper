from googleapiclient.discovery import build
from google.oauth2 import service_account
import io

from googleapiclient.errors import HttpError
from pdfminer.high_level import extract_text
import logging
logging.getLogger('pdfminer').setLevel(logging.ERROR)

CREDS_JSON_PATH = "configs/ostlab-hr-b79582d6308b.json"


def initialize_google_drive_api():
    credentials = service_account.Credentials.from_service_account_file(
        CREDS_JSON_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)

# Function to extract text from Google Docs
def extract_text_from_google_doc(doc_url, service=None):
    if service is None:
        service = initialize_google_drive_api()
    # Extract document ID from the URL
    doc_id = doc_url.split('/')[5]
    try:
        # Export the document as plain text
        doc = service.files().export(fileId=doc_id, mimeType='text/plain').execute()
        # Decode the content from bytes to a UTF-8 string
        return doc.decode('utf-8')
    except HttpError as e:
        if "fileNotExportable" in str(e):
            print(f"File {doc_id} is not exportable as plain text.")
            return "fileNotExportable"
        else:
            raise  # Re-raise the exception if it's not due to fileNotExportable


# Function to download a PDF file
def download_pdf_file(pdf_url, service=None):
    if service is None:
        service = initialize_google_drive_api()
    # Extract file ID from the URL
    pdf_id = pdf_url.split('/')[5]
    # Request the file media content
    request = service.files().get_media(fileId=pdf_id)
    # Store the file content in a BytesIO object
    file = io.BytesIO(request.execute())
    return file


def extract_text_from_pdf(pdf_file_path):
    try:
        text = extract_text(pdf_file_path)
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


