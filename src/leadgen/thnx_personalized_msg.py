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


class PersonalizedThanksMessage(BaseModel):
    # Reasoning: Why this message is being sent to this recipient
    reasoning: str = Field(..., description="Brief reasoning for sending this message (e.g., shared interests, mutual connections, or admiration for their work)." )
    # Greeting and gratitude
    greeting: str = Field( ..., description="Brief greeting and thanks for connecting.")
    # Admiration for the recipient’s mission or achievements
    admiration: str = Field( ..., description="Mention of the recipient’s company mission or achievements.")
    # Specific mention of technologies or projects
    specific_mention: str = Field( default="", description="If there is enough information to fill in this field, otherwise leave it empty string. Specific project or technology that impresses you.")
    # One-sentence introduction to Ostlab company
    company_intro: str = Field( ..., description="Brief description of OstLab’s mission.")
    # Connection between IT and their field
    connection: str = Field( ..., max_length=100, description="How IT complements their work or shared vision.")
    # Offer to stay in touch
    stay_in_touch: str = Field(..., description="Polite offer to stay in touch and learn from them.")
    # Closing gratitude
    closing: str = Field(..., description="Final thanks and compliment.")

def format_thanks_message(extraction: PersonalizedThanksMessage) -> str:
    message_parts = [
        f"{extraction.greeting}",
        f"\n\n{extraction.admiration}"
        f"{f' {extraction.specific_mention}' if extraction.specific_mention else ''}",
        f"\n\n{extraction.company_intro} {extraction.connection}",
        f"\n\n{extraction.stay_in_touch} {extraction.closing}"
    ]
    formatted_message = " ".join(message_parts)
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


def generate_personalized_message(row: pd.Series, tone: str = "friendly",
                                  llm_handler: LLMHandler = None, model: str = "gpt-4.1-nano") -> str:
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
                f"to draft personalized LinkedIn thank-you messages. "
                f"The message should be concise, warm, and professional. "
                f"Follow the provided structure and adapt if some details are missing. "
                f"Use a {tone} tone."
            )
        },
        {
            "role": "user",
            "content": (
                f"Draft a LinkedIn thank-you message using the following details:\n\n"
                f"Recipient Details:\n"
                f"- Recipient’s First Name: {row['First Name']}\n"
                f"- Recipient’s Company: {row['Company Name']}\n"
                f"- Recipient’s Company Description: {row['Company Desc']}\n"
                f"{additional_info_str}\n\n"
                f"User Info:\n"
                f"- Name: {USER_FIRST_NAME}\n"
                f"- Position: {USER_POSITION}\n"
                f"- Company: {USER_COMPANY}\n"
                f"- Company Description: {USER_COMPANY_DESC}\n"
                f"- Company Mission: {USER_COMPANY_MISSION}\n"
                f"- Company Focus: {USER_COMPANY_FOCUS}\n\n"
                f"Message Structure:\n"
                f"1. Greeting and thanks for connecting.\n"
                f"2. Personal admiration for the recipient’s company mission or achievements.\n"
                f"3. Specific mention of their technologies or projects. If there is enough information to fill in this field, otherwise leave it empty string. \n"
                f"4. One sentence about OstLab’s mission and your role.\n"
                f"5. Connection between AI and their field.\n"
                f"6. Offer to stay in touch and collaborate.\n"
                f"7. Closing gratitude and signature with your name and position."
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
            response_format=PersonalizedThanksMessage
        )
        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']
        return format_thanks_message(extraction)
    except Exception as e:
        logger.error(f"failed: {e}")
        traceback_info = f"Traceback: {traceback.format_exc()}"
        logger.error(traceback_info)
        return traceback_info

