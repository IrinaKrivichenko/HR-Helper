import json
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
import re
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class GitHubExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for GitHub extraction")
    github_urls: List[str] = Field(default=[],
                                   description="Extracted GitHub URLs in normalized format (https://github.com/username)")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

    @validator("github_urls", each_item=True)
    def normalize_github_url(cls, url: str) -> str:
        """Normalizes GitHub URL to https://github.com/username format."""
        # Remove spaces and extra characters
        url = url.strip().strip('/').strip('.')

        # If this is a @username reference
        if url.startswith('@'):
            return f"https://github.com/{url[1:]}"

        # If this is a GitHub Pages URL (username.github.io)
        if '.github.io' in url:
            # Extract username from GitHub Pages URL
            match = re.search(r'(?:https?://)?([^.]+)\.github\.io', url)
            if match:
                username = match.group(1)
                return f"https://github.com/{username}"

        # If this is a short link like github.com/username
        if url.startswith('github.com/'):
            return f"https://{url}"

        # If this is already a full GitHub URL
        if url.startswith('https://github.com/'):
            # Extract just the username part
            parts = url.replace('https://github.com/', '').split('/')
            if parts and parts[0]:
                return f"https://github.com/{parts[0]}"

        # If this is just a username
        if re.match(r'^[a-zA-Z0-9\-_]+$', url):
            return f"https://github.com/{url}"

        return url


def extract_cv_github(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts GitHub profiles from CV text using LLM.
    Returns a dictionary with extracted GitHub URLs and metadata.
    """
    start_time = time.time()
    # Patterns for searching GitHub profiles and GitHub Pages
    github_patterns = [
        r'github\.com/[^\s/]+',  # Links like github.com/username
        r'@[^\s/]+',  # Mentions like @username (if context indicates GitHub)
        r'https?://github\.com/[^\s/]+',  # Full links like https://github.com/username
        r'[a-zA-Z0-9\-_]+\.github\.io(?:/[^\s]*)?',  # GitHub Pages like username.github.io/portfolio
        r'https?://[a-zA-Z0-9\-_]+\.github\.io(?:/[^\s]*)?',  # Full GitHub Pages URLs
    ]

    # Extract context with potential GitHub profiles
    cv_text = get_section_for_field(cv_sections, "Github")
    github_context = extract_context_by_patterns(cv_text, github_patterns)

    # Prompt for LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert GitHub profile extractor. "
                "Your task is to extract GitHub profile URLs from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract valid GitHub profile URLs and GitHub Pages URLs.\n"
                "2. Normalize all URLs to the format: https://github.com/username.\n"
                "3. For GitHub Pages URLs (username.github.io), extract the username and convert to https://github.com/username.\n"
                "4. Ignore repository links (with /repo-name), organization pages, or non-profile links.\n"
                "5. Return only the normalized GitHub profile URLs.\n"
                "6. Provide reasoning for each extracted URL.\n"
                "7. If no valid GitHub profiles are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract GitHub profile URLs from the following text:\n\n{github_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=GitHubExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "GitHub": ', '.join(extraction.github_urls) if extraction.github_urls else "",
            "Reasoning about GitHub": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_GitHub_CV_extraction": model,
            "Completion Tokens of_GitHub_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_GitHub_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_GitHub_CV_extraction": cost_info['total_cost'],
            "Confidence_GitHub": extraction.confidence,
            "Time" : time.time()-start_time,
        }

        # Log the complete response in a single entry
        logger.info(
            f"Field extraction completed - Field: 'GitHub' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"GitHub extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "GitHub": "",
            "Reasoning about GitHub": f"Extraction failed: {e}",
            "Model of_GitHub_CV_extraction": model,
            "Completion Tokens of_GitHub_CV_extraction": "0",
            "Prompt Tokens _of_GitHub_CV_extraction": "0",
            "Cost_of_GitHub_CV_extraction": 0.0,
            "Confidence_GitHub": "low",
            "Time" : time.time()-start_time,
        }

        # Log the error response
        logger.info(
            f"Field extraction completed - Field: 'GitHub' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result
