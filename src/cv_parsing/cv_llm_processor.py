import re
from typing import Dict

from src.cv_parsing.info_extraction.cv_llm_email import extract_cv_email
from src.cv_parsing.info_extraction.cv_llm_expertise import extract_cv_expertise
from src.cv_parsing.info_extraction.cv_llm_github import extract_cv_github
from src.cv_parsing.info_extraction.cv_llm_industries import extract_cv_domains_and_industries
from src.cv_parsing.info_extraction.cv_llm_linkedin import extract_cv_linkedin
from src.cv_parsing.info_extraction.cv_llm_location import extract_cv_location
from src.cv_parsing.info_extraction.cv_llm_name import extract_cv_name
from src.cv_parsing.info_extraction.cv_llm_phone import extract_cv_phone
from src.cv_parsing.info_extraction.cv_llm_roles import extract_cv_roles
from src.cv_parsing.info_extraction.cv_llm_seniority import extract_cv_seniority
from src.cv_parsing.info_extraction.cv_llm_stack import extract_cv_stack
from src.cv_parsing.info_extraction.cv_llm_telegram import extract_cv_telegram
from src.cv_parsing.info_extraction.cv_llm_whatsapp import extract_cv_whatsapp
from src.data_processing.nlp.llm_handler import LLMHandler

import time
import traceback
from concurrent.futures import ThreadPoolExecutor

def turn_phones_to_whatsapp_links(phone_numbers_str: str) -> str:
    """
    Converts a comma-separated string of international phone numbers into a comma-separated string of WhatsApp links.
    Args:
        phone_numbers_str: Comma-separated string of phone numbers (e.g., "+375291234567,+375298765432").
    Returns:
        Comma-separated string of WhatsApp links (e.g., "https://wa.me/375291234567, https://wa.me/375298765432").
    """
    if not phone_numbers_str:
        return ""
    # Split by comma, strip whitespace, and filter out empty strings
    phone_numbers = [num.strip() for num in phone_numbers_str.split(",") if num.strip()]
    # Generate WhatsApp links for each valid international number
    whatsapp_links = []
    for num in phone_numbers:
        # Remove all non-digit characters except '+'
        cleaned_num = re.sub(r'[^\d+]', '', num)
        if re.match(r'^\+\d{10,15}$', cleaned_num):
            whatsapp_links.append(f"https://wa.me/{cleaned_num.lstrip('+')}")
    return ", ".join(whatsapp_links)


def extract_cv_info(cv: Dict, llm_handler: LLMHandler):
    """
    Extracts all CV data in parallel using ThreadPoolExecutor.
    Combines results from all extraction functions into a single dictionary.
    Tracks execution time for each field extraction.

    Args:
        cv (str): The CV text to analyze.
        llm_handler (LLMHandler): Instance of LLMHandler for API calls.

    Returns:
        dict: Combined dictionary with all extracted data and timing information.
    """
    # Start timing the entire parallel extraction process
    overall_start_time = time.time()

    # Define the extraction tasks as a list of tuples: (function, model, field_name)
    extraction_tasks = [
        (extract_cv_name, "gpt-4.1-nano", "Name"),
        (extract_cv_seniority, "gpt-4.1-nano", "Seniority"),
        (extract_cv_roles, "gpt-4.1-mini", "Roles"),
        (extract_cv_expertise, "gpt-4.1-nano", "Expertise"),
        (extract_cv_stack, "gpt-4.1", "Stack"),
        (extract_cv_domains_and_industries, "gpt-4.1-nano", "IT Domains and Industries"),
        (extract_cv_linkedin, "gpt-4.1-nano", "LinkedIn"),
        (extract_cv_telegram, "gpt-4.1-nano", "Telegram"),
        (extract_cv_whatsapp, "gpt-4.1-nano", "WhatsApp"),
        (extract_cv_phone, "gpt-4.1-nano", "Phone"),
        (extract_cv_email, "gpt-4.1-nano", "Email"),
        (extract_cv_github, "gpt-4.1-nano", "GitHub"),
        (extract_cv_location, "gpt-4.1-nano", "Location")
    ]

    field_times = {}
    error_logs = []

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
            field_name = extraction_tasks[i][2]
            try:
                extracted_data = future.result()

                # Extract and save Time field if it exists
                if isinstance(extracted_data, dict):
                    if "Time" in extracted_data:
                        field_times[field_name] = extracted_data["Time"]
                        # Remove Time field from the extracted data
                        del extracted_data["Time"]

                    # Add the extracted data to the results dictionary
                    for key, value in extracted_data.items():
                        # Use the field_name prefix if the key might collide with other extractions
                        new_key = f"{field_name}_{key}" if key in results else key
                        results[new_key] = value
                else:
                    results[field_name] = extracted_data

            except Exception as e:
                # Append error log with number, field name, and traceback
                error_logs.append(
                    f"Error #{len(error_logs) + 1} - Extracting Field: {field_name}\n"
                    f"Traceback:\n{traceback.format_exc()}\n"
                    f"{'=' * 50}\n"
                )
                print(f"Error extracting {field_name}: {e}")
                continue

    # Calculate actual total time (parallel execution time)
    total_parallel_time = time.time() - overall_start_time

    # Sort field times to find the longest running task
    sorted_times = sorted(field_times.items(), key=lambda x: x[1], reverse=True)

    # Create timing summary string with each field on a new line
    timing_lines = []

    # Add header with total time and longest operation
    if field_times:
        max_field = sorted_times[0][0]
        max_time = sorted_times[0][1]
        timing_lines.append(f"Total time: {total_parallel_time:.1f} sec")
        timing_lines.append(f"Longest operation: {max_field} ({max_time:.1f} sec)")
        timing_lines.append(f"{'=' * 35}")
        timing_lines.append("Individual field times:")

        # Add each field time on a new line
        for field_name, time_taken in sorted_times:
            # Format with padding for alignment and 1 decimal place
            timing_lines.append(f"  {field_name:<15}: {time_taken:>5.1f} sec")
    else:
        timing_lines.append(f"Total parallel execution: {total_parallel_time:.1f} sec")

    # Join all lines with newline character
    timing_summary = "\n".join(timing_lines)

    if not results.get("WhatsApp"):
        phone_field = results.get("Phone", "")
        whatsapp_links = turn_phones_to_whatsapp_links(phone_field)
        if whatsapp_links:
            results["WhatsApp"] = whatsapp_links

    # Add timing summary to results
    results["Parsing Step3 Time (extract fields)"] = timing_summary
    results["Error Logs"] = "".join(error_logs) if error_logs else ""

    return results
