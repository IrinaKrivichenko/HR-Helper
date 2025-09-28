import json
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.logger import logger  # Added logger import


class TelegramExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for Telegram extraction")
    telegram_contacts: List[str] = Field(default=[],
                                         description="Extracted Telegram contacts in normalized format (@username or https://t.me/username)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("telegram_contacts", each_item=True)
    def normalize_telegram_contact(cls, contact: str) -> str:
        """Normalizes Telegram contact to the format: @username or https://t.me/username"""
        contact = contact.strip().strip('/')
        # If it's a mention like @username
        if contact.startswith('@'):
            return contact
        # If it's a short link like t.me/username
        if contact.startswith('t.me/'):
            return f"https://t.me/{contact.split('/')[-1]}"
        # If it's a full link like https://t.me/username
        if contact.startswith('https://t.me/'):
            return contact
        # If it's just a username
        if re.match(r'^[a-zA-Z0-9_]+$', contact):
            return f"https://t.me/{contact}"
        return contact


def extract_cv_telegram(
        cv_sections: Dict,
        llm_handler: Any,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts Telegram contacts from CV text using LLM.
    Returns a dictionary with extracted Telegram contacts and metadata.
    """
    start_time = time.time()
    # Patterns for searching Telegram contacts
    telegram_patterns = [
        r'@\w+',  # Mentions like @username
        r't\.me/\w+',  # Links like t.me/username
        r'telegram\.me/\w+',  # Links like telegram.me/username
        r'https?://t\.me/\w+',  # Links like https://t.me/username
        r'https?://telegram\.me/\w+',  # Links like https://telegram.me/username
    ]

    # Extract context with potential Telegram contacts
    cv_text = get_section_for_field(cv_sections, "Telegram")
    telegram_context = extract_context_by_patterns(cv_text, telegram_patterns)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert Telegram contact extractor. "
                "Your task is to extract Telegram usernames or links from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid Telegram usernames or links.\n"
                "2. Normalize all contacts to one of the following formats:\n"
                "   - @username\n"
                "   - https://t.me/username\n"
                "3. Ignore Twitter usernames, email addresses, or other social media links.\n"
                "4. Return only the normalized Telegram contacts.\n"
                "5. Provide reasoning for each extracted contact.\n"
                "6. If no valid Telegram contacts are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract Telegram contacts from the following text:\n\n{telegram_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=TelegramExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "Telegram": ', '.join(extraction.telegram_contacts) if extraction.telegram_contacts else "",
            "Reasoning about Telegram": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_Telegram_CV_extraction": model,
            "Completion Tokens of_Telegram_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Telegram_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Telegram_CV_extraction": cost_info['total_cost'],
            "Confidence_Telegram": extraction.confidence,
            "Time" : time.time()-start_time,
        }

        # Log the complete response in a single entry
        logger.info(
            f"Field extraction completed - Field: 'Telegram' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"Telegram extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "Telegram": "",
            "Reasoning about Telegram": f"Extraction failed: {e}",
            "Model of_Telegram_CV_extraction": model,
            "Completion Tokens of_Telegram_CV_extraction": "0",
            "Prompt Tokens of_Telegram_CV_extraction": "0",
            "Cost_of_Telegram_CV_extraction": 0.0,
            "Confidence_Telegram": "low",
            "Time" : time.time()-start_time,
        }

        # Log the error response
        logger.info(
            f"Field extraction completed - Field: 'Telegram' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result
