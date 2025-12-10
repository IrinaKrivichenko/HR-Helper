from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_languages import extract_vacancy_languages
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_industries import extract_vacancy_industries
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_location import extract_vacancy_location
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_rate import extract_vacancy_rate
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_roles import extract_vacancy_role
from src.candidate_matching.vacancy_processing.info_extraction.vacancy_llm_technologies import \
    extract_vacancy_technologies

from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler

import concurrent.futures

def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler):
    # Use ThreadPoolExecutor to run the functions concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit both tasks to the executor
        future1 = executor.submit(extract_vacancy_technologies, vacancy,  llm_handler, model="gpt-4.1-mini")
        future2 = executor.submit(extract_vacancy_role, vacancy,  llm_handler, model="gpt-4.1-nano") # SGR
        future3 = executor.submit(extract_vacancy_industries, vacancy, llm_handler, model="gpt-4.1-nano")
        future4 = executor.submit(extract_vacancy_location, vacancy, llm_handler, model="gpt-4.1-mini")
        future5 = executor.submit(extract_vacancy_rate, vacancy, llm_handler, model="gpt-4.1-nano") # SGR
        future6 = executor.submit(extract_vacancy_languages, vacancy,  llm_handler, model="gpt-4.1-nano")

        # Retrieve the results
        extracted_data1 = future1.result()
        extracted_data2 = future2.result()
        extracted_data3 = future3.result()
        extracted_data4 = future4.result()
        extracted_data5 = future5.result()
        extracted_data6 = future6.result()



    # Combine the rest of the fields
    extracted_data ={k: v for d in [extracted_data1, extracted_data2,
                                     extracted_data3, extracted_data4,
                                     extracted_data5, extracted_data6]
                           for k, v in d.items()}

    # logger.info(f"extracted_data['Vacancy Reasoning']: {extracted_data.get('Vacancy Reasoning', 'No reasoning provided')}")
    return extracted_data

