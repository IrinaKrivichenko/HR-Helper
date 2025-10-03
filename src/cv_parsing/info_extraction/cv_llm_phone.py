import json
import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field, validator
import re
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class PhoneExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for phone extraction")
    phone_numbers: List[str] = Field(default=[],
                                     description="Extracted phone numbers in international format (+<country_code><number>)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("phone_numbers", each_item=True)
    def normalize_phone_number(cls, phone: str) -> str:
        """Normalizes phone number to international format: +<country_code><number>"""
        # Remove all non-digit characters except '+'
        digits = re.sub(r'[^\d+]', '', phone)
        # If the number is already in international format, return it
        if digits.startswith('+'):
            return digits
        # If the number starts with '00', replace it with '+'
        if digits.startswith('00'):
            return f"+{digits[2:]}"
        # If the number starts with a digit, assume it's a local number
        # (You can add logic to determine the country code from context here)
        return f"+{digits}"


def extract_cv_phone(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts phone numbers from CV text using LLM.
    Returns a dictionary with extracted phones and metadata.
    """
    start_time = time.time()
    # Patterns for searching potential phones
    phone_patterns = [
        r'\+\d{1,3}[\(\s\-\.]?[\d\s\-\.\(\)]{5,15}\d',  # International numbers
        r'00\d{1,3}[\(\s\-\.]?[\d\s\-\.\(\)]{5,15}\d',  # Numbers with 00
        r'\(\d{1,4}\)[\s\-\.]?[\d\s\-\.]{5,15}\d',  # Numbers with code in brackets
        r'\d{5,15}',  # Local numbers
    ]

    # Extract context with potential phones
    cv_text = get_section_for_field(cv_sections, "Phone")
    phone_context = extract_context_by_patterns(cv_text, phone_patterns)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert phone number extractor. "
                "Your task is to extract phone numbers from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid phone numbers in international format: +<country_code><number>.\n"
                "2. If a phone number is not in international format, normalize it:\n"
                "   - Remove all non-digit characters except '+'.\n"
                "   - If the number starts with '00', replace it with '+'.\n"
                "   - If the number starts with a single '0', remove it (local format).\n"
                "   - Ensure the final number is 10–15 digits long (including country code).\n"
                "3. Ignore fax numbers, internal extensions, or invalid numbers.\n"
                "4. Return only the normalized phone numbers in international format.\n"
                "5. Provide reasoning for each extracted number.\n"
                "6. If no valid phone numbers are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract phone numbers from the following text:\n\n{phone_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=1000,
            response_format=PhoneExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "Phone": ', '.join(extraction.phone_numbers) if extraction.phone_numbers else "",
            "Reasoning about Phone": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_Phone_CV_extraction": model,
            "Completion Tokens of_Phone_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Phone_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Phone_CV_extraction": cost_info['total_cost'],
            "Confidence_Phone": extraction.confidence,
            "Time" : time.time()-start_time,
        }

        # Log the complete response in a single entry
        logger.info(f"Field extraction completed - Field: 'Phone' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"Phone extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "Phone": "",
            "Reasoning about Phone": f"Extraction failed: {e}",
            "Model of_Phone_CV_extraction": model,
            "Completion Tokens of_Phone_CV_extraction": "0",
            "Prompt Tokens _of_Phone_CV_extraction": "0",
            "Cost_of_Phone_CV_extraction": 0.0,
            "Confidence_Phone": "low",
            "Time" : time.time()-start_time,
        }

        # Log the error response
        logger.info(f"Field extraction completed - Field: 'Phone' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result
