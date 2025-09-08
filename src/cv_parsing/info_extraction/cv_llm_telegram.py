from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re

from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns


class TelegramExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for Telegram extraction")
    telegram_contacts: List[str] = Field(default=[], description="Extracted Telegram contacts in normalized format (@username or https://t.me/username)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

def extract_cv_telegram(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano",
    add_tokens_info: bool = False
) -> Dict[str, Any]:
    """
    Extracts Telegram contacts from CV text using LLM.
    Returns a dictionary with extracted Telegram contacts and metadata.
    """
    # Patterns for searching Telegram contacts
    telegram_patterns = [
        r'@\w+',  # Mentions like @username
        r't\.me/\w+',  # Links like t.me/username
        r'telegram\.me/\w+',  # Links like telegram.me/username
        r'https?://t\.me/\w+',  # Links like https://t.me/username
        r'https?://telegram\.me/\w+',  # Links like https://telegram.me/username
    ]

    # Extract context with potential Telegram contacts
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

    # Отправляем запрос в LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=TelegramExtraction
        )
        extraction = response['parsed']
        cost = response['cost']['total_cost']

        # Формируем результат
        result = {
            "Telegram": ', '.join(extraction.telegram_contacts) if extraction.telegram_contacts else "",
        }

        if add_tokens_info:
            result.update({
                "Reasoning about Telegram": "\n".join(extraction.reasoning_steps),
                "Model Used": model,
                "Cost": f"${cost:.6f}",
                "Confidence": extraction.confidence,
            })
        else:
            result["Cost_of_Telegram_CV_extraction"] = cost

        return result
    except Exception as e:
        print(f"Telegram extraction failed: {e}")
        if add_tokens_info:
            return {
                "Telegram": "",
                "Reasoning about Telegram": f"Extraction failed: {e}",
                "Model Used": model,
                "Cost": "$0.000000",
                "Confidence": "low",
            }
        else:
            return {
                "Telegram": "",
                "Cost_of_Telegram_CV_extraction": 0.0,
            }
