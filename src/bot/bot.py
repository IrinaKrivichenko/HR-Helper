import asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.utils import send_message
from src.candidate_matching.matcher import match_candidats
from src.logger import logger
from src.nlp.llm_handler import LLMHandler
from src.bot.authorization import auth_manager


import os
from dotenv import load_dotenv
load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the /start command is issued."""
    await update.message.reply_text("Hey! Glad you're here!")

async def process_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_name = user.username if user.username else user.first_name
    text = update.message.text
    if not auth_manager.is_user_authorized(user_name):
        print(f"NOT authorized {user_name} have send: ({text})")
        await auth_manager.add_user(user_name, text, update)
    else:
        print(f"authorized {user_name} have send: ({text})")
        if not await auth_manager.remove_user(user_name, text, update):
            await send_message(update, "Please wait.")
            # pd.set_option('display.max_colwidth', None)
            llm_handler = LLMHandler()
            await match_candidats(update, text, user_name, llm_handler)

application = ApplicationBuilder().token(os.getenv("TOKEN")).build()
# # Adding a handler for the /start command
# application.add_handler(CommandHandler("start", start))
# Adding a handler for text messages
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_request))
auth_manager.set_application(application)


