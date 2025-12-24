import traceback
from typing import Optional
import pandas as pd
from pydantic import BaseModel, Field
from datetime import datetime
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger

# Constants for the user (Andrus)
USER_FIRST_NAME = "Andrus"
USER_POSITION = "CEO & Co-Founder"
USER_COMPANY = "OstLab"
USER_COMPANY_DESC = "AI-driven solutions for businesses"
USER_COMPANY_MISSION = "help businesses leverage artificial intelligence to enhance operations and achieve goals"
USER_COMPANY_FOCUS = "developing and implementing tailored AI solutions"

class FollowUpMessage(BaseModel):
    greeting: str = Field(..., max_length=50, description="Casual greeting and well-wishing.")
    connection_mention: str = Field(..., max_length=50, description="Mention of previous connection.")
    interest_question: str = Field(..., max_length=120, description="Question or interest in their work, challenges, or experience.")
    stay_in_touch: str = Field(..., max_length=100, description="Offer to stay in touch and potential collaboration. Use word 'nice'")

def format_follow_up_message(extraction: FollowUpMessage) -> str:
    message_parts = [
        f"{extraction.greeting}",
        f"\n{extraction.connection_mention} {extraction.interest_question}",
        f"\n{extraction.stay_in_touch}"
    ]
    formatted_message = "\n".join(message_parts)
    return formatted_message

def extract_years_since_founded(founded_str: str) -> Optional[int]:
    try:
        year = None
        for word in founded_str.split():
            if word.isdigit() and len(word) == 4:
                year = int(word)
                break
        if year is not None:
            current_year = datetime.now().year
            return current_year - year
    except:
        pass
    return None

def generate_follow_up_message(row: pd.Series, tone: str = "friendly",
                                llm_handler: LLMHandler = None, model: str = "gpt-4.1-nano") -> str:
    company_decr = row['Company Desc'] if row['Company Desc'] else f"{row['Why Relevant Now']} \n\n{row['Signals']}"

    years_since_founded = None
    if "Founded" in row and pd.notna(row["Founded"]):
        years_since_founded = extract_years_since_founded(row["Founded"])

    additional_fields = [
        ("Recipient’s Company Age", f"{years_since_founded} years" if years_since_founded else None),
        ("Recipient’s Company Size", row.get("Company size")),
        ("Recipient’s Company Location", row.get("Company location / relevant office")),
        ("Recipient’s Company Motto", row.get("Company Motto"))
    ]
    additional_info = []
    for field_name, field_value in additional_fields:
        if field_value and pd.notna(field_value):
            additional_info.append(f"- {field_name}: {field_value}")
    additional_info_str = "\n".join(additional_info)

    prompt = [
        {
            "role": "system",
            "content": (
                f"You are a professional assistant helping {USER_FIRST_NAME}, {USER_POSITION} at {USER_COMPANY}, "
                f"to draft a follow-up LinkedIn message for someone they connected with earlier. "
                f"The message should be on equal terms but respectful, concise, warm, friendly, and professional, but not pushy. "
                f"Use fewer compliments (1-2 compliments are enough). "
                f"Make one small grammatical or punctuation mistake to make it sound more natural. "
                f"Ask about their challenges, tools, or ways they use AI, depending on the information about their company. "
                "Use neutral and less emotionally charged language."
                f"Be brief."
            )
        },
        {
            "role": "user",
            "content": (
                f"Draft a LinkedIn follow-up message using the following details:\n\n"
                f"Recipient Details:\n"
                f"- Recipient’s First Name: {row['First Name']}\n"
                f"- Recipient’s Company: {row['Company Name']}\n"
                f"- Recipient’s Company Description: {company_decr}\n"
                f"{additional_info_str}\n\n"
                f"User Info:\n"
                f"- Name: {USER_FIRST_NAME}\n"
                f"- Position: {USER_POSITION}\n"
                f"- Company: {USER_COMPANY}\n"
                f"- Company Description: {USER_COMPANY_DESC}\n"
                f"- Company Mission: {USER_COMPANY_MISSION}\n"
                f"- Company Focus: {USER_COMPANY_FOCUS}\n\n"
                f"Message Structure:\n"
                f"1. Casual greeting and well-wishing.\n"
                f"2. Mention of previous connection and following their progress.\n"
                f"3. Admiration for their work or achievements.\n"
                f"4. Personal appreciation for insights or contributions they've shared (optional).\n"
                f"5. Offer to stay in touch and learn more about their work."
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
            temperature=1,
            response_format=FollowUpMessage
        )
        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']
        return format_follow_up_message(extraction)
    except Exception as e:
        logger.error(f"Failed to generate follow-up message: {e}")
        traceback_info = f"Traceback: {traceback.format_exc()}"
        logger.error(traceback_info)
        return traceback_info
