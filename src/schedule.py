import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from src.google_services.sheets import read_specific_columns, remove_extra_spaces_from_headers, \
    initialize_google_sheets_api
# from src.nlp.embedding_handler import add_embeddings_column
from src.bot.authorization import  auth_manager


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
    # add_embeddings_column(df, write_columns=True)

def setup_scheduler():
    """Setup and start the task scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(auth_manager.reset_authorized_users, 'cron', hour=0, minute=59)
    scheduler.add_job(prepare_google_sheets, 'cron', hour=1, minute=1)

    scheduler.start()



prepare_google_sheets()
