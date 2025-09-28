import json
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.logger import logger  # Added logger import


class LinkedInExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for LinkedIn extraction")
    linkedin_urls: List[str] = Field(default=[],
                                     description="Extracted LinkedIn URLs in normalized format (https://linkedin.com/in/<username>)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("linkedin_urls", each_item=True)
    def normalize_linkedin_url(cls, url: str) -> str:
        """Normalizes LinkedIn URL to the format: https://www.linkedin.com/in/username"""
        url = url.strip().strip('/').strip('.')
        # If it's a short URL without https
        if url.startswith('linkedin.com/in/'):
            return f"https://www.linkedin.com/in/{url.split('/')[-1]}"
        # If it's a full URL with https
        if url.startswith('https://www.linkedin.com/in/'):
            return url
        # If it's a full URL without www
        if url.startswith('https://linkedin.com/in/'):
            return url.replace('https://linkedin.com', 'https://www.linkedin.com')
        # If it's just a username
        if re.match(r'^[a-zA-Z0-9\-_]+$', url):
            return f"https://www.linkedin.com/in/{url}"
        return url


def extract_cv_linkedin(
        cv_sections: Dict,
        llm_handler: Any,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts LinkedIn profiles from CV text using LLM.
    Returns a dictionary with extracted LinkedIn URLs and metadata.
    """
    start_time = time.time()
    # Patterns for searching LinkedIn profiles
    linkedin_patterns = [
        r'linkedin\.com/in/[^\s/]+',  # Links like linkedin.com/in/username
        r'linkedin\.com/[^\s/]+',  # Links like linkedin.com/username
        r'in/[^\s/]+',  # Links like in/username
    ]

    # Extract context with potential LinkedIn profiles
    cv_text = get_section_for_field(cv_sections, "Linkedin")
    linkedin_context = extract_context_by_patterns(cv_text, linkedin_patterns)

    # Prompt for LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert LinkedIn profile extractor. "
                "Your task is to extract LinkedIn profile URLs from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid LinkedIn profile URLs.\n"
                "2. Normalize all URLs to the format: https://linkedin.com/in/<username>.\n"
                "3. Ignore company pages, job postings, or non-profile links.\n"
                "4. Return only the normalized LinkedIn profile URLs.\n"
                "5. Provide reasoning for each extracted URL.\n"
                "6. If no valid LinkedIn profiles are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract LinkedIn profile URLs from the following text:\n\n{linkedin_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=1000,
            response_format=LinkedInExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "LinkedIn": ', '.join(extraction.linkedin_urls) if extraction.linkedin_urls else "",
            "Reasoning about LinkedIn": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_LinkedIn_CV_extraction": model,
            "Completion Tokens of_LinkedIn_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_LinkedIn_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_LinkedIn_CV_extraction": cost_info['total_cost'],
            "Confidence_LinkedIn": extraction.confidence,
            "Time" : time.time()-start_time,
        }

        # Log the complete response in a single entry
        logger.info(
            f"Field extraction completed - Field: 'LinkedIn' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"LinkedIn extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "LinkedIn": "",
            "Reasoning about LinkedIn": f"Extraction failed: {e}",
            "Model of_LinkedIn_CV_extraction": model,
            "Completion Tokens of_LinkedIn_CV_extraction": "0",
            "Prompt Tokens _of_LinkedIn_CV_extraction": "0",
            "Cost_of_LinkedIn_CV_extraction": 0.0,
            "Confidence_LinkedIn": "low",
            "Time" : time.time()-start_time,
        }

        # Log the error response
        logger.info(
            f"Field extraction completed - Field: 'LinkedIn' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result
