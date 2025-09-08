from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.cv_parsing.info_extraction.context_by_patterns import extract_context_by_patterns


class EmailExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step reasoning for email extraction")
    emails: List[str] = Field(default=[], description="Extracted email addresses")
    confidence: str = Field(description="Confidence in extraction (high/medium/low)")

def extract_cv_email(
    cv_text: str,
    llm_handler: Any,
    model: str = "gpt-4.1-nano",
    add_tokens_info: bool = False
) -> Dict[str, Any]:
    """
    Extracts email addresses from CV text using LLM.
    Returns a dictionary with extracted emails and metadata.
    """
    # Patterns for searching email addresses
    email_patterns = [
        r'\b[\w.-]+@[\w.-]+\.\w+\b',  # Standard pattern for email
    ]

    # Extract context with potential email addresses
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

    try:
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=400,
            response_format=EmailExtraction
        )
        extraction = response['parsed']
        cost = response['cost']['total_cost']

        result = {
            "Email": ', '.join(extraction.emails) if extraction.emails else "",
        }

        if add_tokens_info:
            result.update({
                "Reasoning about Email": "\n".join(extraction.reasoning_steps),
                "Model Used": model,
                "Cost": f"${cost:.6f}",
                "Confidence": extraction.confidence,
            })
        else:
            result["Cost_of_Email_CV_extraction"] = cost

        return result
    except Exception as e:
        print(f"Email extraction failed: {e}")
        if add_tokens_info:
            return {
                "Email": "",
                "Reasoning about Email": f"Extraction failed: {e}",
                "Model Used": model,
                "Cost": "$0.000000",
                "Confidence": "low",
            }
        else:
            return {
                "Email": "",
                "Cost_of_Email_CV_extraction": 0.0,
            }
