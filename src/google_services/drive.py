from googleapiclient.discovery import build
from google.oauth2 import service_account
import io
import logging
import re

from docx import Document
from pdfminer.high_level import extract_text


logging.getLogger('pdfminer').setLevel(logging.ERROR)
CREDS_JSON_PATH = "configs/ostlab-hr-b79582d6308b.json"

def initialize_google_drive_api():
    """Initializes Google Drive API service."""
    credentials = service_account.Credentials.from_service_account_file(
        CREDS_JSON_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)


def extract_text_from_docx(file_path):
    """Extracts text from DOCX file."""
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return None



def extract_text_from_pdf(pdf_source):
    """Extracts text from PDF (file path or BytesIO)."""
    try:
        if isinstance(pdf_source, str):
            return extract_text(pdf_source)
        elif isinstance(pdf_source, io.BytesIO):
            return extract_text(pdf_source)
        else:
            raise ValueError("Unsupported PDF source type.")
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_google_file(url: str, service=None):
    """
    Extracts text from Google Drive file (Doc or PDF).
    Raises ValueError if URL is invalid or doc_id cannot be extracted.
    Raises HttpError if access is denied or file is not found.
    """
    if service is None:
        service = initialize_google_drive_api()

    doc_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not doc_id_match:
        raise ValueError("Could not extract document ID from URL. Invalid URL format.")
    doc_id = doc_id_match.group(1)

    # Checking file type by MIME-type (more reliable than by URL)
    file_metadata = service.files().get(fileId=doc_id, fields="mimeType").execute()
    mime_type = file_metadata.get('mimeType', '')

    if mime_type == 'application/vnd.google-apps.document':
        # Google Doc
        doc = service.files().export(fileId=doc_id, mimeType='text/plain').execute()
        return doc.decode('utf-8')

    elif mime_type == 'application/pdf':
        # PDF
        request = service.files().get_media(fileId=doc_id)
        pdf_file = io.BytesIO(request.execute())
        return extract_text_from_pdf(pdf_file)

    else:
        raise ValueError(f"Unsupported file type: {mime_type}")

