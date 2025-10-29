from src.data_processing.nlp.llm_handler import LLMHandler, parse_token_usage_and_cost

import re
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict
import math
from random import randint

class ExtractedRate(BaseModel):
    """Structured representation of the extracted rate from a vacancy."""
    value: float = Field(description=f"Maximum numerical value of the rate extracted from the vacancy description.")
    currency: Literal["$", "€", "£"] = Field(description="Currency for the rate specified in the vacancy.")
    period: Literal["per hour", "per day", "per week", "per month", "per year", "fixed"] = Field(description="Mentioned payment period.")

class VacancyRateResponse(BaseModel):
    """Structured response for vacancy rate extraction."""
    reasoning: str = Field(description="Brief explanation of how the rate was extracted from the vacancy text.")
    false_positives_analysis: str = Field(description="Analysis of any numbers that could be mistaken for a rate ")
    rate: Optional[ExtractedRate] = Field(default=None, description="May be None if rate is not specified.")

def parse_extracted_rate(extracted_rate: ExtractedRate) -> Optional[ExtractedRate]:
    """
    Parses the extracted rate string into a structured `ExtractedRate` object.
    """
    if extracted_rate is None:
        return "No rate specified"
    try:
        value = extracted_rate.value
        if value == 0 :
            return "No rate specified"
        currency = extracted_rate.currency
        period = extracted_rate.period
        if period == "per day":
            value = value / 8
            period = "per hour"
        elif period == "per week":
            value = value / 40
            period = "per hour"
        elif period == "per month":
            value = value / 168  # 40 hours/week * 4.2 weeks/month
            period = "per hour"
        elif period == "per year":
            value = value / 2080  # 40 hours/week * 52 weeks/year
            period = "per hour"
        rounded_value = math.ceil(value * 100) / 100
        return f"{rounded_value:.2f} {currency} {period}"
    except Exception:
        return "No rate specified"

def parse_llm_vacancy_rate(response, add_tokens_info) -> VacancyRateResponse:
    extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']
    model = response['model']

    reasoning = f"{extraction.reasoning}\n\n{extraction.false_positives_analysis}"
    rate_data = extraction.rate
    rate = parse_extracted_rate(rate_data)

    # Build result dictionary
    if add_tokens_info:
        result: Dict[str, str] = {
            "Extracted Rate": rate,
            "Vacancy Rate Reasoning": reasoning,
            "Model Used vacancy_rate": model,
            "Completion Tokens vacancy_rate": str(usage.completion_tokens),
            "Prompt Tokens vacancy_rate": str(usage.prompt_tokens),
            "Cost vacancy_rate": str(cost_info['total_cost'])
        }
    else:
        result: Dict[str, str] = {
            "Extracted Rate": rate,
            "Vacancy Rate Reasoning": reasoning,
            "Model Used vacancy_rate": model,
            "Cost vacancy_rate": str(cost_info['total_cost'])
        }

    return result

def extract_vacancy_rate(vacancy: str, llm_handler: LLMHandler, model, add_tokens_info: bool = False):
    """
    Extracts rate from the vacancy description using the language model (LLM).
    Args:
    - vacancy (str): The vacancy description.
    - llm_handler (LLMHandler): Handler for interacting with the language model.
    Returns:
    - dict: A dictionary containing the extracted information.
    """
    exml = randint(25, 65)
    # Define the prompt for the language model
    prompt = [
        {
            "role": "system",
            "content": "You are an expert in extracting salary/rate information from job vacancies. "
                       "Your task is to carefully review the job descriptions, extract rate information (if any), "
                       "and present it in a structured format."
        },
        {
            "role": "user",
            "content": (
                "Your task is to process the provided job description and extract the rate information:\n\n"
                "1. Reasoning: Provide a brief reasoning on how you extracted the rate from the job description. \n"
                "   - If no rate is found, explain why."
                "2. False Positives Analysis: "
                "   - Double-check: Make sure you don't confuse the rate with other parameters like duration, budget, team size and etc."
                "2. Identify the rate or salary mentioned in the job description."
                f"  - If a range is provided, such as '{exml-5}-{exml}$ per hour', return the highest value ({exml}). "
                "3.  Determine the payment period using these rules:\n"
                "   - If the rate value is less than 100, most likely the period indicated 'per hour'.\n"
                "   - If the rate value is greater than 1000, most likely 'per month'.\n"
                "   - If the description mentions 'per hour', 'hourly', '/hr', or '/hour', or 'rate' (without mentioning other periods) use 'per hour'.\n"
                "   - If the description mentions 'per day', 'daily', or '/day', use 'per day'.\n"
                "   - If the description mentions 'per week', 'weekly', or '/week', use 'per week'.\n"
                "   - If the description mentions 'per month', 'monthly', 'gross', or 'salary' (without mentioning other periods), use 'per month'.\n"
                "   - If the description mentions 'per year', 'annual', or 'yearly', use 'per year'.\n"
                "   - If the description mentions 'fixed price', 'project fee', or 'lump sum', use 'fixed'.\n"
                "   - If no period is specified, default to 'per month' for salaries and 'per hour' for freelance/contract rates.\n"
                "4. Identify the period."
                f"If no rate or salary is specified, return 'None'.\n"
                f"\n"                
                "Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\"\n"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = max(len(vacancy) , 500)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens, response_format=VacancyRateResponse)
    # Parse the response from the LLM
    extracted_data = parse_llm_vacancy_rate(response, add_tokens_info=add_tokens_info)
    return extracted_data





#
# def parse_extracted_rate(rate_str):
#     """
#     Parses the 'Extracted Rate' string according to specified conditions.
#     Args:
#     - rate_str (str): The rate string to parse.
#     Returns:
#     - str: The parsed rate as a string.
#     """
#     if not rate_str or '$' not in rate_str:
#         return rate_str
#
#     # Extract numerical values from the rate string
#     numbers = re.findall(r'\d+', rate_str)
#     if not numbers:
#         return rate_str
#
#     numbers = [int(num) for num in numbers]
#     if 'per hour' in rate_str.lower():
#         return rate_str
#         # If there's a range, take the second number; otherwise, take the first
#         rate = max(numbers) if len(numbers) > 1 else numbers[0]
#         return str(rate)
#     elif 'per day' in rate_str.lower():
#         # If there's a range, take the second number; otherwise, take the first
#         rate = max(numbers) if len(numbers) > 1 else numbers[0]
#         hourly_rate = rate / 8
#         rounded_rate = math.ceil(hourly_rate * 100) / 100
#         return f"{rounded_rate:.2f}$ per hour"
#     elif 'per week' in rate_str.lower():
#         # If there's a range, take the second number; otherwise, take the first
#         rate = max(numbers) if len(numbers) > 1 else numbers[0]
#         hourly_rate = rate / 40
#         rounded_rate = math.ceil(hourly_rate * 100) / 100
#         return f"{rounded_rate:.2f}$ per hour"
#     elif 'per month' in rate_str.lower():
#         # If there's a range, take the second number; otherwise, take the first
#         rate = max(numbers) if len(numbers) > 1 else numbers[0]
#         hourly_rate = rate / 168
#         rounded_rate = math.ceil(hourly_rate * 100) / 100
#         return f"{rounded_rate:.2f}$ per hour"
#     else:
#         return rate_str
#
#
# def parse_llm_vacancy_rate(response: str, add_tokens_info: bool) -> dict:
#     # Initialize a dictionary to store extracted data
#     extracted_data = {}
#
#     # Split the response into sections
#     sections = response.split('##')
#
#     # Iterate over each section to extract relevant information
#     for section in sections:
#         if ':' in section:
#             # Split section into name and content
#             section_name, section_content = section.split(':', 1)
#             section_name = section_name.strip()
#             section_content = section_content.strip()
#
#             # Extract programming languages if present
#             if section_name == 'Reasoning':
#                 extracted_data['Vacancy Reasoning'] = section_content
#
#             # Extract rate if present
#             elif section_name == 'Extracted Rate':
#                 extracted_data['Extracted Rate'] = parse_extracted_rate(section_content)
#
#             elif section_name == 'Token Usage and Cost':
#                 token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_rate", add_tokens_info=add_tokens_info)
#                 extracted_data.update(token_data)
#
#     return extracted_data
#
#
#
# def extract_vacancy_rate(vacancy: str, llm_handler: LLMHandler, model, add_tokens_info: bool = False):
#     """
#     Extracts rate from the vacancy description using the language model (LLM).
#     Args:
#     - vacancy (str): The vacancy description.
#     - llm_handler (LLMHandler): Handler for interacting with the language model.
#     Returns:
#     - dict: A dictionary containing the extracted information.
#     """
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": "You are an expert in analyzing job descriptions and determining expected rate based on text descriptions. Your task is to carefully review the job descriptions, extract rate information (if any), and present it in a structured format."
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Your task is to process the provided job description and extract the following information:\n\n"
#                 "1. Reasoning: Provide a brief reasoning on how you extracted the rate from the job description. \n"
#                 "2. Identify the rate or salary mentioned in the job description. The rate should be formatted as a number followed by a currency symbol and the period, for example, '10000$ per month'. "
#                 f"If a range is provided, such as '25-28$ per hour', return it as a range with the period. If phrases like 'up to' are used, extract the numerical value and assume it is per month unless otherwise specified. "
#                 f"If no rate or salary is specified, return 'No rate is specified'.\n"
#                 "## Extracted Rate: The rate extracted by the language model from the vacancy description.\n"
#                 f"\n"
#                 "Here is an example:\n\n"
#                 "# Example Input:\n"
#                 f"Американская компания в поиске опытного ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas. Уровень английского: C1. Зарплата - до 8000-10000$ gross.\n"
#                 f"\n"
#                 "# Example Output:\n"
#                 "## Reasoning: The salary mentioned is up to 8000-10000$ gross, which is interpreted as 8000-10000$ per month.\n"
#                 "## Extracted Rate: 8000-10000$ per month\n"
#                 "\n"
#                 "Here is the input:\n\n"
#                 f"# Job Description:\n"
#                 f"{vacancy}\"\n"
#             )
#         }
#     ]
#
#     # Calculate max tokens based on the length of the vacancy description
#     max_tokens = max(len(vacancy) * 3, 500)
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_vacancy_rate(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data
#
#

