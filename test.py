import logging
import os

import pandas as pd
from telegram import Update, Message
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from src.data_processing.nlp.llm_handler import LLMHandler
from src.google_services.sheets import read_specific_columns, write_dict_to_sheet
from src.leadgen.publishing.publication_interest_evaluator import evaluate_publication_interest
from src.leadgen.publishing.publication_translator import translate_and_classify_post


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


columns = [
    "First Name",
    "Lead Position",
    "Company Name",
    "Company size",
    "Company Industries",
    "Company location / relevant office",
    "Company Motto",
    "Company Desc",
    "Company Website",
    "Specialties",
    "Signals",
]

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message = update.message
    if hasattr(message, 'forward_origin') and hasattr(message.forward_origin, 'chat') and message.forward_origin.chat != "belaiplatform":


        publication_text = message.text or message.caption or ""
        if not publication_text:
            await message.reply_text("No text found in the forwarded message.")
            return
        print(publication_text)

        df = read_specific_columns(
            columns_to_extract=columns,
            sheet_name="Leads CRM",
            spreadsheet_env_name="ΛV_LINKEDIN_LEADGEN_SPREADSHEET_ID",
        )
        if df.empty or len(df) <= 89:
            await message.reply_text("Error: Lead data not found or invalid index.")
            return
        lead_row = df.iloc[89]

        llm_handler = LLMHandler()
        translation_and_classification = translate_and_classify_post(
                                publication_text,
                                model="gpt-4.1-nano",
                                llm_handler=llm_handler
                            )
        evaluation_result = evaluate_publication_interest(
                                row=lead_row,
                                publication_text=translation_and_classification["translated_text"],
                                model="gpt-4.1-nano",
                                llm_handler=llm_handler,
                            )

        origin_chat_username = message.forward_origin.chat.username
        origin_chat_message_i = message.forward_origin.message_id
        original_post_link = f"t.me/{origin_chat_username}/{origin_chat_message_i}"
        post_info = {
            "original post link": original_post_link,
            "original post text": publication_text,
            "date of original post publication": message.forward_origin.date.strftime('%Y-%m-%d %a'),
            "classification": translation_and_classification["classification"],
            "classification reasoning": translation_and_classification["reasoning"],
            "interest score": evaluation_result["interest_score"],
            "reasoning for interest score": evaluation_result["reasoning"],
            "post text translated to English": translation_and_classification["translated_text"]
        }

        # Записываем данные в таблицу
        write_dict_to_sheet(
                                data_dict=post_info,
                                spreadsheet_env_name="РUBLICATIONS_SPREADSHEET_ID",
                                sheet_name="BelAI"
                            )
        await message.reply_text(evaluation_result)

def main() -> None:
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_forwarded_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()


