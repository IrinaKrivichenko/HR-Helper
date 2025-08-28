import os
from dotenv import load_dotenv
load_dotenv()

from telegram import Update

from src.bot.utils import send_message
from src.cv_parsing.cv_llm_processor import extract_cv_info
from src.cv_parsing.info_extraction.cv_llm_languages import cv_languages_processing
from src.google_services.sheets import write_dict_to_sheet
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
    write_dict_to_sheet(data_dict=extracted_data, sheet_name="staff")

    doc_id = os.getenv("SHEET_ID")
    page_id = os.getenv("CANDIDATES_SHEET_ID")
    full_name = " ".join([extracted_data["First Name"], extracted_data["Last Name"]])
    google_sheet_row_link = f"<a href='https://docs.google.com/spreadsheets/d/{doc_id}/edit#gid={page_id}&range=A2'>{full_name} CV is parsed</a>"
    await send_message(update, google_sheet_row_link)
    # for field in extracted_data:
    #     if "Cost" not in field:
    #         await send_message(update, field)
    #         await send_message(update, extracted_data[field])

