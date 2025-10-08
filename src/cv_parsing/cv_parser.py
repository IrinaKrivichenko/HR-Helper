import time
import traceback

from src.cv_parsing.cv_llm_processor import extract_cv_info
from src.cv_parsing.info_extraction.cv_llm_languages import cv_languages_processing
from src.cv_parsing.sections.section_identifier import identify_resume_sections
from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler


async def parse_cv(cv_text: str, llm_handler: LLMHandler = None) -> dict:
    start_time = time.time()
    extracted_data = {"Original CV text": cv_text}
    logs = []  # List to accumulate logs for all steps

    try:
        if not cv_text or len(cv_text)<100:
            logs.append(
                f"Error in Step 0: Reading file\n"
                # f"Traceback:\n{traceback.format_exc()}\n"
                f"{'=' * 50}\n"
            )
            raise

        if llm_handler is None:
            llm_handler = LLMHandler()

        # Step 1: Process CV languages
        try:
            cv_text, languages_extracted_data = cv_languages_processing(cv_text, llm_handler=llm_handler)
            extracted_data.update(languages_extracted_data)
        except Exception as e:
            logs.append(
                f"Error in Step 1: Process CV languages\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                f"{'=' * 50}\n"
            )
            raise  # Re-raise to stop execution or handle as needed

        # Step 2: Identify CV sections
        try:
            cv_sections = identify_resume_sections(cv_text, llm_handler=llm_handler)
            extracted_data.update(cv_sections)
        except Exception as e:
            logs.append(
                f"Error in Step 2: Identify CV sections\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                f"{'=' * 50}\n"
            )
            raise

        # Step 3: Extract CV info
        try:
            cv_info = extract_cv_info(cv=cv_sections, llm_handler=llm_handler)
            extracted_data.update(cv_info)
        except Exception as e:
            logs.append(
                f"Error in Step 3: Extract CV info\n"
                f"Traceback:\n{traceback.format_exc()}\n"
                f"{'=' * 50}\n"
            )
            raise

    except Exception as e:
        # Add accumulated logs to extracted_data
        extracted_data["Error Logs"] = "".join(logs) if logs else ""

    # Calculate total parsing time
    extracted_data["Total CV parsing time"] = time.time() - start_time

    logger.info(f"extracted_data from cv: {str(extracted_data)}")
    return extracted_data
