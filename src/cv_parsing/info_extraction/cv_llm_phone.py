from typing import Dict, Any, List
from pydantic import BaseModel, Field, validator
import re

from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns


class PhoneExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for phone extraction")
    phone_numbers: List[str] = Field(default=[], description="Extracted phone numbers in international format (+<country_code><number>)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

def extract_cv_phone(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano",
    add_tokens_info: bool = False
) -> Dict[str, Any]:
    """
    Extracts phone numbers from CV text using LLM.
    Returns a dictionary with extracted phones and metadata.
    """
    # Patterns for searching potential phones
    phone_patterns = [
        r'\+\d{1,3}[\(\s\-\.]?[\d\s\-\.\(\)]{5,15}\d',  # International numbers
        r'00\d{1,3}[\(\s\-\.]?[\d\s\-\.\(\)]{5,15}\d',  # Numbers with 00
        r'\(\d{1,4}\)[\s\-\.]?[\d\s\-\.]{5,15}\d',  # Numbers with code in brackets
        r'\d{5,15}',  # Local numbers
    ]

    # Extracting context with potential phones
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
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=1000,
            response_format=PhoneExtraction
        )
        extraction = response['parsed']
        cost = response['cost']['total_cost']

        result = {
            "Phone": ', '.join(extraction.phone_numbers) if extraction.phone_numbers else "",
        }

        if add_tokens_info:
            result.update({
                "Reasoning about Phone": "\n".join(extraction.reasoning_steps),
                "Model Used": model,
                "Cost": f"${cost:.6f}",
                "Confidence": extraction.confidence,
            })
        else:
            result["Cost_of_Phone_CV_extraction"] = cost

        return result
    except Exception as e:
        print(f"Phone extraction failed: {e}")
        if add_tokens_info:
            return {
                "Phone": "",
                "Reasoning about Phone": f"Extraction failed: {e}",
                "Model Used": model,
                "Cost": "$0.000000",
                "Confidence": "low",
            }
        else:
            return {
                "Phone": "",
                "Cost_of_Phone_CV_extraction": 0.0,
            }
