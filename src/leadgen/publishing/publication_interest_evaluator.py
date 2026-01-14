import traceback
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger

class PublicationInterestScore(BaseModel):
    reasoning: str = Field(..., description="Reasoning why the publication might be interesting or not to the lead.")
    interest_score: int = Field(..., description="Interest percentage (0 to 100).")

def format_interest_score(extraction: PublicationInterestScore) -> str:
    formatted_output = (
        f"Reasoning: {extraction.reasoning}\n"
        f"Interest Score: {extraction.interest_score}%"
    )
    return formatted_output

def evaluate_publication_interest(
    row: pd.Series,
    publication_text: str,
    model: str,
    llm_handler: LLMHandler = None
) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    recipient_location = row.get("Company location / relevant office", "Unknown")

    # Collect all available lead details
    lead_details = {
        "First Name": row.get("First Name"),
        "Lead Position": row.get("Lead Position"),
        "Company Name": row.get("Company Name"),
        "Company Size": row.get("Company size"),
        "Company Industries": row.get("Company Industries"),
        "Company Location": recipient_location,
        "Company Motto": row.get("Company Motto"),
        "Company Desc": row.get("Company Desc"),
        "Company Website": row.get("Company Website"),
        "Specialties": row.get("Specialties"),
        "Signals": row.get("Signals")
    }

    # Filter out None or empty values
    lead_info = [
        f"- {field}: {value}"
        for field, value in lead_details.items()
        if value and pd.notna(value)
    ]
    lead_info_str = "\n".join(lead_info)

    prompt = [
        {
            "role": "system",
            "content": (
                f"You are an analyst evaluating how interesting a publication is for a lead. "
                f"Use **only English** for analysis. "
                f"Assess the publication on a scale from 0 to 100% based on the lead's details, including their position, company, location, and industry. "
                f"Consider relevance, usefulness, and connection to their business, technologies, or interests. "
                f"If the publication aligns with their industry, location, or specialties, increase the interest score. "
                f"If the publication is irrelevant, decrease the score. "
                f"Provide a concise reasoning in the 'reasoning' field. "
                f"Current date: {current_date}. Lead's location: {recipient_location}."
            )
        },
        {
            "role": "user",
            "content": (
                f"Evaluate how interesting the following publication is for the lead:\n\n"
                f"Lead Details:\n{lead_info_str}\n\n"
                f"Publication Text:\n{publication_text}"
            )
        }
    ]

    try:
        if llm_handler is None:
            llm_handler = LLMHandler()
        response = llm_handler.get_answer(
            prompt,
            model=model,
            max_tokens=1000,
            temperature=0.3,
            response_format=PublicationInterestScore
        )
        extraction = response['parsed']
        return format_interest_score(extraction)
    except Exception as e:
        logger.error(f"Error evaluating interest: {e}")
        traceback_info = f"Traceback: {traceback.format_exc()}"
        logger.error(traceback_info)
        return traceback_info

