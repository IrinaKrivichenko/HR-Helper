from dotenv import load_dotenv

from src.bot.utils import send_message

load_dotenv()

# bot.py
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

import os

async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.username if user.username else user.first_name
    text = update.message.text
    await send_message(update, f"Hi, {user_name}. Your have sent me {text}")




BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, handle_forwarded))
app.run_polling()
