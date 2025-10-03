import json
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns
from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class EmailExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for email extraction")
    emails: List[str] = Field(default=[], description="Extracted email addresses")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")


def extract_cv_email(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts email addresses from CV text using LLM.
    Returns a dictionary with extracted emails and metadata.
    """
    start_time = time.time()
    # Patterns for searching email addresses
    email_patterns = [
        r'\b[\w.-]+@[\w.-]+\.\w+\b',  # Standard pattern for email
    ]

    # Extract context with potential email addresses
    cv_text = get_section_for_field(cv_sections, "Email")
    email_context = extract_context_by_patterns(cv_text, email_patterns)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert email extractor. "
                "Your task is to extract email addresses from the provided text. "
                "Follow these rules strictly:\n"
                "1. Extract only valid email addresses.\n"
                "2. Ignore invalid or fake email addresses (e.g., 'example@example.com' if it's a placeholder).\n"
                "3. Return only the valid email addresses.\n"
                "4. Provide reasoning for each extracted email.\n"
                "5. If no valid email addresses are found, return an empty list."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract email addresses from the following text:\n\n{email_context}"
            )
        }
    ]

    # Send request to LLM
    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=EmailExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Build result dictionary
        result: Dict[str, Any] = {
            "Email": ', '.join(extraction.emails) if extraction.emails else "",
            "Reasoning about Email": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Model of_Email_CV_extraction": model,
            "Completion Tokens of_Email_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Email_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Email_CV_extraction": cost_info['total_cost'],
            "Confidence_Email": extraction.confidence,
            "Time" : time.time()-start_time
        }

        # Log the complete response in a single entry
        logger.info(f"Field extraction completed - Field: 'Email' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"Email extraction failed: {e}")

        # Build error result dictionary
        result: Dict[str, Any] = {
            "Email": "",
            "Reasoning about Email": f"Extraction failed: {e}",
            "Model of_Email_CV_extraction": model,
            "Completion Tokens of_Email_CV_extraction": "0",
            "Prompt Tokens _of_Email_CV_extraction": "0",
            "Cost_of_Email_CV_extraction": 0.0,
            "Confidence_Email": "low",

        }

        # Log the error response
        logger.info(f"Field extraction completed - Field: 'Email' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result
