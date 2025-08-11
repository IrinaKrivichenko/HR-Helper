import asyncio
import traceback

from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes
from docx import Document
from PyPDF2 import PdfReader
# import textract

from src.bot.utils import send_message
from src.candidate_matching.matcher import match_candidats
from src.logger import logger
from src.nlp.llm_handler import LLMHandler
from src.bot.authorization import auth_manager


import os
from dotenv import load_dotenv
load_dotenv()

import os
import traceback
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes
from docx import Document

async def extract_text_from_document(document) -> str:
    file = await document.get_file()
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    file_path = f"downloads/{document.file_name}"
    await file.download_to_drive(file_path)

    extension = os.path.splitext(file_path)[1].lower()
    try:
        if extension == '.docx':
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        elif extension == '.pdf':
            pdf_reader = PdfReader(file_path)
            return "\n".join([page.extract_text() for page in pdf_reader.pages])
        else:
            raise ValueError(f"Unsupported file extension: {extension}")
    finally:
        # Удаляем файл после обработки
        if os.path.exists(file_path):
            os.remove(file_path)

async def process_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_name = user.username if user.username else user.first_name
    text = update.message.text

    if not auth_manager.is_user_authorized(user_name):
        print(f"NOT authorized {user_name} have send: ({text})")
        await auth_manager.add_user(user_name, text, update)
    else:
        print(f"authorized {user_name} have send: ({text})")
        try:
            if update.message.document:
                document = update.message.document
                text = await extract_text_from_document(document)
                await send_message(update, text)

            elif update.message.text:
                text = update.message.text

                if text.lower() in auth_manager.passwords:
                    await update.message.reply_text("You are already authorized.")
                elif not await auth_manager.remove_user(user_name, text, update):
                    if "#available" in text:
                        await update.message.reply_text("The message contains '#available'.")
                    else:
                        # await send_message(update, text)
                        await send_message(update, "Please wait.")
                        llm_handler = LLMHandler()
                        await match_candidats(update, text, user_name, llm_handler)
        except Exception as e:
            logger.error(f"{str(e)}\n{traceback.format_exc()}")
            await update.message.reply_text(f"Please forward this message to @irina_199: An error occurred: {str(e)}")

application = ApplicationBuilder().token(os.getenv("TOKEN")).build()

# Adding handlers for text messages and files
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_request))
application.add_handler(MessageHandler(filters.Document.ALL, process_user_request))

auth_manager.set_application(application)

