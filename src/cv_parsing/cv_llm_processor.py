import traceback

from src.cv_parsing.info_extraction.cv_llm_expertise import extract_cv_expertise
from src.cv_parsing.info_extraction.cv_llm_industry import extract_cv_industry
from src.cv_parsing.info_extraction.cv_llm_languages import extract_cv_languages
from src.cv_parsing.info_extraction.cv_llm_name import extract_cv_name
from src.cv_parsing.info_extraction.cv_llm_re_contacts import extract_contacts
from src.cv_parsing.info_extraction.cv_llm_roles import extract_cv_roles
from src.cv_parsing.info_extraction.cv_llm_seniority import extract_cv_seniority
from src.cv_parsing.info_extraction.cv_llm_stack import extract_cv_stack
from src.nlp.llm_handler import LLMHandler

from concurrent.futures import ThreadPoolExecutor

def extract_cv_info(cv: str, llm_handler: LLMHandler):#, extract_cv_roles=None):
    """
       Extracts all CV data in parallel using ThreadPoolExecutor.
       Combines results from all extraction functions into a single dictionary.

       Args:
           cv (str): The CV text to analyze.
           llm_handler (LLMHandler): Instance of LLMHandler for API calls.

       Returns:
           dict: Combined dictionary with all extracted data.
       """
    # Define the extraction tasks as a list of tuples: (function, model, key_prefix)
    extraction_tasks = [
        (extract_cv_name, "gpt-4o-mini", "Name"),
        (extract_cv_seniority, "gpt-4.1-nano", "Seniority"),
        (extract_cv_roles, "gpt-4o-mini", "Roles"),
        (extract_cv_expertise, "gpt-4.1-nano", "Expertise"),
        (extract_cv_stack, "gpt-4.1", "Stack"),
        (extract_cv_industry, "gpt-4o-mini", "Industry"),
        (extract_contacts, "gpt-4o-nano", "Contacts")
        # (extract_cv_linkedin, "gpt-4.1-nano", "LinkedIn"),
        # (extract_cv_telegram, "gpt-4.1-nano", "Telegram"),
        # (extract_cv_phone, "gpt-4.1-nano", "Phone"),
        # (extract_cv_email, "gpt-4.1-nano", "Email"),
        # # (extract_cv_location, "gpt-4.1-nano", "Location"),
    ]
    # Create a ThreadPoolExecutor
    with ThreadPoolExecutor() as executor:
        # Submit all tasks and store futures in a list
        futures = [
            executor.submit(task[0], cv, llm_handler, model=task[1])
            for task in extraction_tasks
        ]
        # Retrieve results as they complete
        results = {}
        for i, future in enumerate(futures):
            try:
                extracted_data = future.result()
                key_prefix = extraction_tasks[i][2]
                # Add the extracted data to the results dictionary
                if isinstance(extracted_data, dict):
                    for key, value in extracted_data.items():
                        # Use the key_prefix if the key might collide with other extractions
                        new_key = f"{key_prefix}_{key}" if key in results else key
                        results[new_key] = value
                else:
                    results[key_prefix] = extracted_data
            except Exception as e:
                print(f"Error extracting {extraction_tasks[i][2]}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                continue
    return results



