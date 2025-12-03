from datetime import datetime


from tzlocal import get_localzone

from src.leadgen.tg_external_bots.RDNKLeadBot import find_lead_pattern, parse_lead_text
from src.bot.utils import send_answer_message
from src.candidate_matching.matcher import match_candidats
from src.cv_parsing.cv_parser import parse_cv
from src.cv_parsing.save_cv import save_cv_info
from src.google_services.drive import extract_text_from_google_file, extract_text_from_docx, extract_text_from_pdf
from src.google_services.drive_authorization import start_google_drive_auth, handle_oauth_callback
from src.google_services.sheets import write_dict_to_sheet
from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler
from src.bot.authorization import auth_manager
from src.leadgen.leadgen_reminder import leadgen_reminder

from dotenv import load_dotenv
load_dotenv()

# bot.py
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

import os
import traceback
import logging

logging.getLogger("pdfminer.pdffont").setLevel(logging.ERROR)


async def process_lead(update: Update, text: str,   user_name: str):
    lead_dict = parse_lead_text(text)
    lead_dict["#"] = "=A3+1"
    local_timezone = get_localzone()
    lead_dict["Datetime"] = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
    lead_dict["TG user"] = f"t.me/{user_name}"
    write_dict_to_sheet(data_dict=lead_dict, sheet_name="Leads2", spreadsheet_env_name='ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID')
    await send_answer_message(update, f"Lead {lead_dict['Company']} is parsed")

async def process_cv(update: Update, text: str,  file_path: str,   user_name: str, llm_handler):
    await send_answer_message(update, f"Parsing CV")
    extracted_data = await parse_cv(text, llm_handler)
    message_to_user = save_cv_info(extracted_data, file_path)
    await send_answer_message(update, message_to_user)

async def process_vacancy(update: Update, text: str,  user_name: str, llm_handler):
    await send_answer_message(update, "Searching for candidates....")
    await match_candidats(update, text, user_name, llm_handler)

async def extract_text_from_document(document):
    try:
        file = await document.get_file()
        if not os.path.exists("downloads"):
            os.makedirs("downloads")
        file_path = f"downloads/{document.file_name}"
        await file.download_to_drive(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError("File not found after download.")
        if os.path.getsize(file_path) == 0:
            raise ValueError("Downloaded file is empty.")
        extension = os.path.splitext(file_path)[1].lower()
        if extension == '.docx':
            extracted_text = extract_text_from_docx(file_path)
        elif extension == '.pdf':
            extracted_text = extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        return extracted_text, file_path
    except Exception as e:
        logger.error(f"Error processing file {document.file_name}: {str(e)}\n{traceback.format_exc()}")
        raise  # Pass the exception to `process_user_request`


async def process_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main handler for user requests."""


    user = update.effective_user
    user_name = user.username if user.username else user.first_name
    text = update.message.text
    file_path = None
    try:
        if text is not None:
            if find_lead_pattern(text):
                await process_lead(update, text, user_name)
                return
            # Check if the user is @AndrusKr or @irina_199
            if user_name in ["AndrusKr", "irina_199"]:
                if text == "disk":
                    await start_google_drive_auth(update, context)
                    return
                elif text.startswith(os.getenv("GOOGLE_OAUTH_REDIRECT_URI")):
                    await handle_oauth_callback(update, context)
                    return
                elif text.lower() == "leadgen":
                    await leadgen_reminder.remind_to_send_message()
                    return

        if await auth_manager.is_user_authorized(user_name, text, update):
            if update.message.document is not None:
                file_text, file_path = await extract_text_from_document(update.message.document)
                text = file_text if text is None else f"Additional message from user: {text}\n\n {file_text}"
                input_type = "CV"
            elif "#available" in text:
                await update.message.reply_text("The message contains '#available'.")
                return
            elif "/folders/" in text :
                await send_answer_message(update, "You have sent a link to a folder.")
                return
            elif ("docs.google.com" in text) or ("drive.google.com" in text):
                text, file_path = extract_text_from_google_file(text)
                input_type = "CV"
            else:
                input_type = "vacancy"

            llm_handler = LLMHandler()
            if input_type == "vacancy":
                await process_vacancy(update, text, user_name, llm_handler)
            elif input_type == "CV":
                await process_cv(update, text,  file_path, user_name, llm_handler)
    except Exception as e:
        logger.error(f"{str(e)}\n{traceback.format_exc()}")
        await update.message.reply_text(f"Please forward this message to @irina_199: {str(e)}")
    finally:
        if file_path is not None and os.path.exists(file_path):
            os.remove(file_path)

application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

# Adding handlers for text messages and files
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_request))
application.add_handler(MessageHandler(filters.Document.ALL, process_user_request))

# Adding handlers for google
application.add_handler(CommandHandler("disk", start_google_drive_auth))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_oauth_callback))

auth_manager.set_application(application)
leadgen_reminder.set_application(application)


