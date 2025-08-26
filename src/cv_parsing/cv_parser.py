
from telegram import Update

from src.bot.utils import send_message
from src.cv_parsing.cv_llm_processor import extract_cv_info
from src.cv_parsing.info_extraction.cv_llm_languages import cv_languages_processing
from src.logger import logger
from src.nlp.llm_handler import LLMHandler
from src.nlp.translator import translate_text_with_llm


async def parse_cv(update: Update,  cv_text, user_name, llm_handler=None) -> None:
    if llm_handler is None:
        llm_handler = LLMHandler()

    cv_text, languages_extracted_data = cv_languages_processing(cv_text, llm_handler=llm_handler)

    extracted_data = extract_cv_info(cv=cv_text, llm_handler=llm_handler)
    extracted_data.update(languages_extracted_data)

    logger.info(f"extracted_data from cv: {str(extracted_data)}")
    for field in extracted_data:
        if "Cost" not in field:
            await send_message(update, field)
            await send_message(update, extracted_data[field])

