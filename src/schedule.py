import asyncio
from datetime import datetime


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from src.google_services.sheets import read_specific_columns, initialize_google_sheets_api
from src.bot.authorization import  auth_manager
from src.leadgen.leadgen_reminder import leadgen_reminder


def prepare_google_sheets():
    service = initialize_google_sheets_api()
    # Define the columns to extract by name
    columns_to_extract = [
        'First Name', 'Last Name', 'LVL of engagement', 'Seniority', 'Main Roles', 'Additional Roles',
        'Stack', 'Industries', 'Expertise', 'Location'
    ]
    # Get specific columns with hyperlinks
    df = read_specific_columns(columns_to_extract, service=service)
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

_asyncio_loop = None

def get_event_loop():
    global _asyncio_loop
    if _asyncio_loop is None or _asyncio_loop.is_closed():
        _asyncio_loop = asyncio.new_event_loop()
    return _asyncio_loop

def run_async_job(async_func, *args, **kwargs):
    loop = get_event_loop()
    try:
        print(f"Running async job: {async_func.__name__}")
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(async_func(*args, **kwargs), loop)
            future.result()
            print(f"Completed async job: {async_func.__name__}")
        else:
            loop.run_until_complete(async_func(*args, **kwargs))
    except Exception as e:
        print(f"Error in run_async_job for {async_func.__name__}: {e}")

def run_async_reset_authorized_users():
    run_async_job(auth_manager.reset_authorized_users)

def run_async_remind_to_send_message():
    run_async_job(leadgen_reminder.remind_to_send_message)


def setup_scheduler():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Scheduler] Current time: {current_time}")

    executors = {'default': ThreadPoolExecutor(max_workers=1)}
    scheduler = BackgroundScheduler(executors=executors)
    scheduler.add_job(
        clear_downloads_folder,
        'cron', hour=1, minute=2
    )
    scheduler.add_job(
        run_async_reset_authorized_users,
        'cron', hour=1, minute=0
    )
    scheduler.add_job(
        run_async_remind_to_send_message,
        'cron', hour=10, minute=0
    )
    scheduler.start()
    print("Scheduler started!")
    return scheduler

prepare_google_sheets()
