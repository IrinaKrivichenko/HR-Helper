from src.candidate_matching.vacancy_processing.vacancy_llm_details import extract_vacancy_details
from src.candidate_matching.vacancy_processing.vacancy_llm_location_and_industry import extract_vacancy_location_and_industry
from src.logger import logger
from src.nlp.llm_handler import LLMHandler

import concurrent.futures

def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
    # Use ThreadPoolExecutor to run the functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit both tasks to the executor
        future1 = executor.submit(extract_vacancy_details, vacancy, llm_handler, model)
        future2 = executor.submit(extract_vacancy_location_and_industry, vacancy, llm_handler, model)

        # Retrieve the results
        extracted_data1 = future1.result()
        extracted_data2 = future2.result()

    # Combine the results
    extracted_data = {**extracted_data1, **extracted_data2}

    logger.info(f"extracted_data['Vacancy Reasoning']: {extracted_data.get('Vacancy Reasoning', 'No reasoning provided')}")

    return extracted_data
