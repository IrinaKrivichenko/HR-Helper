from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re

from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns


class GitHubExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for GitHub extraction")
    github_urls: List[str] = Field(default=[], description="Extracted GitHub URLs in normalized format (https://github.com/username)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("github_urls", each_item=True)
    def normalize_github_url(cls, url: str) -> str:
        """Normalizes GitHub URL to https://github.com/username format."""
        # Remove spaces and extra characters
        url = url.strip().strip('/').strip('.')
        # If this is a @username reference
        if url.startswith('@'):
            return f"https://github.com/{url[1:]}"
        # If this is a short link like github.com/username
        if url.startswith('github.com/'):
            return f"https://{url}"

def extract_cv_github(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano",
    add_tokens_info: bool = False
) -> Dict[str, Any]:
    """
    Extracts GitHub profiles from CV text using LLM.
    Returns a dictionary with extracted GitHub URLs and metadata.
    """
    # Шаблоны для поиска GitHub-профилей
    github_patterns = [
        r'github\.com/[^\s/]+',       # Ссылки вида github.com/username
        r'@[^\s/]+',                  # Упоминания вида @username (если контекст указывает на GitHub)
        r'https?://github\.com/[^\s/]+',  # Полные ссылки вида https://github.com/username
    ]

    # Извлекаем контекст с потенциальными GitHub-профилями
    github_context = extract_context_by_patterns(cv_text, github_patterns)

    # Промпт для LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert GitHub profile extractor. "
                "Your task is to extract GitHub profile URLs from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid GitHub profile URLs.\n"
                "2. Normalize all URLs to the format: https://github.com/username.\n"
                "3. Ignore repository links, organization pages, or non-profile links.\n"
                "4. Return only the normalized GitHub profile URLs.\n"
                "5. Provide reasoning for each extracted URL.\n"
                "6. If no valid GitHub profiles are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract GitHub profile URLs from the following text:\n\n{github_context}"
            )
        }
    ]

    # Отправляем запрос в LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=GitHubExtraction
        )
        extraction = response['parsed']
        cost = response['cost']['total_cost']

        # Формируем результат
        result = {
            "GitHub": ', '.join(extraction.github_urls) if extraction.github_urls else "",
        }

        if add_tokens_info:
            result.update({
                "Reasoning about GitHub": "\n".join(extraction.reasoning_steps),
                "Model Used": model,
                "Cost": f"${cost:.6f}",
                "Confidence": extraction.confidence,
            })
        else:
            result["Cost_of_GitHub_CV_extraction"] = cost

        return result
    except Exception as e:
        print(f"GitHub extraction failed: {e}")
        if add_tokens_info:
            return {
                "GitHub": "",
                "Reasoning about GitHub": f"Extraction failed: {e}",
                "Model Used": model,
                "Cost": "$0.000000",
                "Confidence": "low",
            }
        else:
            return {
                "GitHub": "",
                "Cost_of_GitHub_CV_extraction": 0.0,
            }
