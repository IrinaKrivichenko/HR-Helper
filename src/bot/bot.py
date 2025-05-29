import asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from src.candidate_matching.matcher import match_candidats
from src.logger import logger
from src.nlp.llm_handler import LLMHandler
from src.bot.locks import send_lock


import os
from dotenv import load_dotenv
load_dotenv()


async def process_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_name = user.username if user.username else user.first_name
    text = update.message.text
    logger.info(f"message from {user_name}")
    logger.info(text)
    # pd.set_option('display.max_colwidth', None)
    llm_handler = LLMHandler()
    await match_candidats(update, text, user_name, llm_handler)



application = ApplicationBuilder().token(os.getenv("TOKEN")).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_request))


