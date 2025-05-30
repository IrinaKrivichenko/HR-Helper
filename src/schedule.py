from src.google_services.sheets import read_specific_columns, remove_extra_spaces_from_headers, \
    initialize_google_sheets_api
from src.nlp.embedding_handler import add_embeddings_column
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def prepare_google_sheets():
    service = initialize_google_sheets_api()
    remove_extra_spaces_from_headers(service=service)
    # Define the columns to extract by name
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Seniority', 'Role',
        'Stack', 'Industry', 'Expertise', 'English', 'Location', 'Embedding','Role_Embedding','Stack_Embedding'
    ]
    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract, service=service)
    add_embeddings_column(df, write_columns=True)

def setup_scheduler():
    """Setup and start the task scheduler."""
    scheduler = AsyncIOScheduler()

    # Add a job to run every day at 1 AM
    scheduler.add_job(prepare_google_sheets, 'cron', hour=1, minute=0)

    scheduler.start()


prepare_google_sheets()
