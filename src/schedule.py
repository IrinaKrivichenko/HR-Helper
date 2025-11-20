import asyncio
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from src.google_services.sheets import read_specific_columns, initialize_google_sheets_api
from src.bot.authorization import  auth_manager


def prepare_google_sheets():
    service = initialize_google_sheets_api()
    # Define the columns to extract by name
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Seniority', 'Main Roles', 'Additional Roles',
        'Stack', 'Industries', 'Expertise', 'Location'
    ]
    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract, service=service)
    values_df = read_specific_columns(['Industries Values', 'IT Domains Values'], 'values')
    predefined_industries = list(values_df['Industries Values'])
    predefined_it_domains = list(values_df['IT Domains Values'])
    print("predefined_industries ", len(predefined_industries))
    print("predefined_it_domains ", len(predefined_it_domains))
    import pandas as pd
    industries_values = [val.strip() for val in values_df['Industries Values'].tolist() if val and pd.notna(val)]
    it_domains_values = [val.strip() for val in values_df['IT Domains Values'].tolist() if val and pd.notna(val)]
    print("industries_values", len(industries_values))
    print("it_domains_values", len(it_domains_values))
    list_of_existing_roles = list(read_specific_columns(['Role Values'], 'values')['Role Values'])
    print("list_of_existing_roles", len(list_of_existing_roles))
    print()
    # add_embeddings_column(df, write_columns=True)


def clear_downloads():
    if os.path.exists("downloads"):
        os.makedirs("downloads")

import os
import shutil

def clear_downloads_folder():
    downloads_path = "downloads"
    if not os.path.exists(downloads_path):
        return
    for item in os.listdir(downloads_path):
        item_path = os.path.join(downloads_path, item)
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
                print(f"file removed: {item}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"folder removed: {item}")
        except Exception as e:
            print(f"Not able to remove {item}: {e}")
clear_downloads_folder()


def setup_scheduler():
    """Setup and start the task scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(auth_manager.reset_authorized_users, 'cron', hour=0, minute=59)
    scheduler.add_job(clear_downloads_folder, 'cron', hour=1, minute=1)

    scheduler.start()



prepare_google_sheets()
