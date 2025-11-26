import json
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger

class WhatsAppExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for WhatsApp extraction")
    whatsapp_contacts: List[str] = Field(default=[],
                                         description="Extracted WhatsApp contacts in normalized format (https://wa.me/<number>)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("whatsapp_contacts", each_item=True)
    def normalize_whatsapp_contact(cls, contact: str) -> str:
        """Normalizes WhatsApp contact to the format: https://wa.me/<number>"""
        contact = contact.strip().strip('/')
        # Remove all non-digit characters except '+'
        cleaned_number = re.sub(r'[^\d+]', '', contact)
        # If it's already a wa.me link
        if cleaned_number.startswith('https://wa.me/'):
            return cleaned_number
        # If it's a raw number (with optional '+')
        if re.match(r'^\+\d{10,15}$', cleaned_number):
            return f"https://wa.me/{cleaned_number}"
        # If it's a number without '+', assume international format
        if re.match(r'^\d{10,15}$', cleaned_number):
            return f"https://wa.me/{cleaned_number}"
        return contact

def extract_cv_whatsapp(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts WhatsApp contacts from CV text using LLM.
    Returns a dictionary with extracted WhatsApp contacts and metadata.
    """
    start_time = time.time()

    # Patterns for searching WhatsApp contacts
    whatsapp_patterns = [
        r'wa\.me/\+\d{10,15}',  # Links like wa.me/+1234567890
        r'wa\.me/\d{10,15}',     # Links like wa.me/1234567890
        r'https?://wa\.me/\+\d{10,15}',  # Links like https://wa.me/+1234567890
        r'https?://wa\.me/\d{10,15}',     # Links like https://wa.me/1234567890
        r'\+\d{10,15}',          # Raw numbers like +1234567890
        r'\d{10,15}',            # Raw numbers like 1234567890 (assuming international)
    ]

    # Extract context with potential WhatsApp contacts
    cv_text = get_section_for_field(cv_sections, "WhatsApp")
    whatsapp_context = cv_text # extract_context_by_patterns(cv_text, whatsapp_patterns)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert WhatsApp contact extractor. "
                "Your task is to extract WhatsApp numbers or links from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid WhatsApp numbers or links.\n"
                "2. Normalize all contacts to the format: https://wa.me/<number>.\n"
                "3. Ignore email addresses, other social media links, or invalid numbers.\n"
                "4. Return only the normalized WhatsApp contacts.\n"
                "5. Provide reasoning for each extracted contact.\n"
                "6. If no valid WhatsApp contacts are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract WhatsApp contacts from the following text:\n\n{whatsapp_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=WhatsAppExtraction
        )
        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "WhatsApp": ', '.join(extraction.whatsapp_contacts) if extraction.whatsapp_contacts else "",
            "Reasoning about WhatsApp": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_WhatsApp_CV_extraction": model,
            "Completion Tokens of_WhatsApp_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens of_WhatsApp_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_WhatsApp_CV_extraction": cost_info['total_cost'],
            "Confidence_WhatsApp": extraction.confidence,
            "Time": time.time() - start_time,
        }

        # Log the complete response in a single entry
        logger.info(
            f"Field extraction completed - Field: 'WhatsApp' | Response: {json.dumps(result, ensure_ascii=False)}"
        )
        return result

    except Exception as e:
        logger.error(f"WhatsApp extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "WhatsApp": "",
            "Reasoning about WhatsApp": f"Extraction failed: {e}",
            "Model of_WhatsApp_CV_extraction": model,
            "Completion Tokens of_WhatsApp_CV_extraction": "0",
            "Prompt Tokens of_WhatsApp_CV_extraction": "0",
            "Cost_of_WhatsApp_CV_extraction": 0.0,
            "Confidence_WhatsApp": "low",
            "Time": time.time() - start_time,
        }

        # Log the error response
        logger.info(
            f"Field extraction completed - Field: 'WhatsApp' | Response: {json.dumps(result, ensure_ascii=False)}"
        )
        return result
