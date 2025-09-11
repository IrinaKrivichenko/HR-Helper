
import io
import re

from docx import Document
from googleapiclient.http import MediaFileUpload
from pdfminer.high_level import extract_text

from src.google_services.drive_authorization import load_credentials
from src.logger import logger



from googleapiclient.discovery import build


def initialize_google_drive_api():
    """Initializes Google Drive API service with OAuth."""
    creds = load_credentials()
    if not creds or not creds.valid:
        raise ConnectionError("Please contact @AndrusKr to authorize disk")
    return build('drive', 'v3', credentials=creds)


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
    Extracts text from Google Drive file (Doc or PDF) with hyperlinks and filename.
    Returns tuple: (text_content, filename)

    For Google Docs, hyperlinks are formatted as separate paragraphs: "text_link: url"
    """
    if service is None:
        service = initialize_google_drive_api()

    doc_id = _extract_doc_id(url)
    file_metadata = service.files().get(fileId=doc_id, fields="mimeType,name").execute()

    mime_type = file_metadata.get('mimeType', '')
    filename = file_metadata.get('name', 'Unknown')

    if mime_type == 'application/vnd.google-apps.document':
        text_content = _extract_google_doc_with_links(doc_id, service)
    elif mime_type == 'application/pdf':
        text_content = _extract_pdf_content(doc_id, service)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")

    return text_content, filename

def _extract_doc_id(url: str) -> str:
    """Extract document ID from Google Drive URL."""
    doc_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not doc_id_match:
        raise ValueError("Could not extract document ID from URL. Invalid URL format.")
    return doc_id_match.group(1)

def _extract_pdf_content(doc_id: str, service) -> str:
    """Extract text from PDF file."""
    request = service.files().get_media(fileId=doc_id)
    pdf_file = io.BytesIO(request.execute())
    return extract_text_from_pdf(pdf_file)

def _extract_google_doc_with_links(doc_id: str, drive_service) -> str:
    """Extract text from Google Doc with hyperlinks as separate paragraphs."""
    from googleapiclient.discovery import build
    docs_service = build('docs', 'v1', credentials=drive_service._http.credentials)
    document = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs = []
    doc_content = document.get('body', {}).get('content', [])
    for element in doc_content:
        if 'paragraph' in element:
            paragraph_parts = _process_paragraph(element['paragraph'])
            paragraphs.extend(paragraph_parts)
    return '\n\n'.join(filter(None, paragraphs))


def _process_paragraph(paragraph) -> list:
    """Process paragraph and return list of text parts (regular text + separate links)."""
    parts = []
    current_text = []
    for element in paragraph.get('elements', []):
        if 'textRun' not in element:
            continue
        text_run = element['textRun']
        text = text_run.get('content', '')
        text_style = text_run.get('textStyle', {})
        if 'link' in text_style:
            # Add accumulated regular text first
            if current_text:
                parts.append(''.join(current_text).strip())
                current_text = []
            # Add link as separate paragraph
            link_url = text_style['link'].get('url', '')
            if link_url and text.strip():
                parts.append(f"{text.strip()}: {link_url}")
        else:
            current_text.append(text)
    # Add remaining regular text
    if current_text:
        parts.append(''.join(current_text).strip())

    return parts


def check_or_create_subfolder(parent_folder_id, folder_name, service=None):
    if not service:
        service = initialize_google_drive_api()
   # Check if the subfolder exists
    query = (
        f"parents='{parent_folder_id}' and "
        f"trashed=false"
    )
    print(f"Query: {query}")
    print(f"Parent folder ID: {parent_folder_id}")
    response = service.files().list(
        q=query,
        corpora='allDrives',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields='files(id, name)',
        pageSize=100
    ).execute()
    folders = response.get('files', [])
    print(f"number of folders: {len(folders)}")

    query = (
        f"name='{folder_name}' and "
        f"parents='{parent_folder_id}' and "
        f"trashed=false"
    )
    print(f"Query: {query}")
    print(f"Parent folder ID: {parent_folder_id}")
    response = service.files().list(
        q=query,
        corpora='allDrives',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields='files(id, name)',
        pageSize=100
    ).execute()
    print(f"Response: {response}")
    folders = response.get('files', [])
    if folders:
        return folders[0]['id']
    else:
        # Create the subfolder
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder['id']

def check_file_exists(folder_id, file_name, service=None):
    if not service:
        service = initialize_google_drive_api()
    # Check if the file exists in the folder
    query = f"name='{file_name}' and parents='{folder_id}'"
    response = service.files().list(q=query, spaces='drive').execute()
    return len(response.get('files', [])) > 0

def upload_file_to_drive(file_path, drive_folder_id, drive_file_name, service=None):
    if not service:
        service = initialize_google_drive_api()
    # Determine MIME type depending on file extension
    if file_path.lower().endswith('.pdf'):
        mimetype = 'application/pdf'
    elif file_path.lower().endswith('.docx'):
        mimetype = 'application/vnd.google-apps.document'  # Convert to Google Doc
    else:
        # For other file types, you can use automatic detection
        import mimetypes
        mimetype, _ = mimetypes.guess_type(file_path)
        mimetype = mimetype or 'application/octet-stream'
    # create metadata
    file_metadata = {
        'name': drive_file_name,
        'parents': [drive_folder_id],
        'mimeType': mimetype
    }
    # Upload the file to Google Drive
    media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)
    gdrive_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return gdrive_file.get('id')


def get_file_id(folder_id, file_name, service=None):
    if not service:
        service = initialize_google_drive_api()
    # Get the ID of the existing file
    query = f"name='{file_name}' and parents='{folder_id}'"
    response = service.files().list(q=query, spaces='drive').execute()
    return response.get('files', [{}])[0].get('id', '')

def add_editor_to_file(file_id, editor_email, service=None):
    if not service:
        service = initialize_google_drive_api()
    # Add an editor to the file
    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': editor_email
    }
    service.permissions().create(fileId=file_id, body=permission).execute()




