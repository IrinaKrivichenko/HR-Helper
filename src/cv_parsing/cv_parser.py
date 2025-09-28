import time

from src.cv_parsing.cv_llm_processor import extract_cv_info
from src.cv_parsing.info_extraction.cv_llm_languages import cv_languages_processing
from src.cv_parsing.sections.section_identifier import identify_resume_sections
from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler



async def parse_cv(cv_text, user_name, llm_handler=None) -> dict:
    start_time = time.time()
    if llm_handler is None:
        llm_handler = LLMHandler()

    extracted_data = {"Original CV text": cv_text}
    cv_text, languages_extracted_data = cv_languages_processing(cv_text, llm_handler=llm_handler)

    cv_sections = identify_resume_sections(cv_text, llm_handler=llm_handler)
    extracted_data.update(cv_sections)

    extracted_data.update(extract_cv_info(cv=cv_sections, llm_handler=llm_handler))
    extracted_data.update(languages_extracted_data)
    extracted_data["Total CV parsing time"] = time.time() - start_time

    logger.info(f"extracted_data from cv: {str(extracted_data)}")
    return extracted_data

