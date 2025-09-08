from src.cv_parsing.cv_llm_processor import extract_cv_info
from src.cv_parsing.info_extraction.cv_llm_languages import cv_languages_processing
from src.logger import logger
from src.nlp.llm_handler import LLMHandler



async def parse_cv(cv_text, user_name, llm_handler=None) -> dict:
    if llm_handler is None:
        llm_handler = LLMHandler()

    cv_text, languages_extracted_data = cv_languages_processing(cv_text, llm_handler=llm_handler)

    extracted_data = extract_cv_info(cv=cv_text, llm_handler=llm_handler)
    extracted_data.update(languages_extracted_data)

    logger.info(f"extracted_data from cv: {str(extracted_data)}")
    return extracted_data

