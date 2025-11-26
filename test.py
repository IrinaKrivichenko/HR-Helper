from dotenv import load_dotenv


load_dotenv()

# bot.py
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

import os

# async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     user_name = user.username if user.username else user.first_name
#     text = update.message.text
#     await update.message.reply_text(f"Hi, {user_name}. Your have sent me {text}")
#
#
#
#
# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# app = ApplicationBuilder().token(BOT_TOKEN).build()
# app.add_handler(MessageHandler(filters.ALL, handle_forwarded))
# app.run_polling()

# from telegram import Bot
#
# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# bot = Bot(token=BOT_TOKEN)
# bot.send_message(chat_id=694614399, text='Message text')

import asyncio
from telegram import Bot
load_dotenv()

async def send():
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=694614399, text='Hello')

asyncio.run(send())
