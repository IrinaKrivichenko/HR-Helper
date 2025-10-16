from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_details import extract_vacancy_details
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_industries import extract_vacancy_industries
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_location import extract_vacancy_location
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_rate import extract_vacancy_rate

from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler

import concurrent.futures

def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler):
    # Use ThreadPoolExecutor to run the functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit both tasks to the executor
        future1 = executor.submit(extract_vacancy_details, vacancy,  llm_handler, model="gpt-4o-mini")
        future2 = executor.submit(extract_vacancy_industries, vacancy, llm_handler, model="gpt-4.1-nano")
        future3 = executor.submit(extract_vacancy_location, vacancy, llm_handler, model="gpt-4.1-nano")
        future4 = executor.submit(extract_vacancy_rate, vacancy, llm_handler, model="gpt-4.1-nano")

        # Retrieve the results
        extracted_data1 = future1.result()
        extracted_data2 = future2.result()
        extracted_data3 = future3.result()
        extracted_data4 = future4.result()

    # Extract 'Vacancy Reasoning' from each result and combine them
    vacancy_reasoning_1 = extracted_data1.get('Vacancy Reasoning', '')
    vacancy_reasoning_2 = extracted_data2.get('Vacancy Reasoning', '')
    vacancy_reasoning_3 = extracted_data3.get('Vacancy Reasoning', '')
    vacancy_reasoning_4 = extracted_data4.get('Vacancy Reasoning', '')

    combined_reasoning = ' '.join(reasoning for reasoning in [vacancy_reasoning_1, vacancy_reasoning_2, vacancy_reasoning_3, vacancy_reasoning_4] if reasoning)

    # Create a new dictionary with the combined reasoning
    extracted_data = {
        'Vacancy Reasoning': combined_reasoning
    }

    # Combine the rest of the fields
    extracted_data.update({k: v
                           for d in [extracted_data1, extracted_data2, extracted_data3, extracted_data4]
                           for k, v in d.items()
                           if 'Reasoning' not in k})

    logger.info(f"extracted_data['Vacancy Reasoning']: {extracted_data.get('Vacancy Reasoning', 'No reasoning provided')}")
    return extracted_data

