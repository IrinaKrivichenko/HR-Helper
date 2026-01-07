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
USER_COMPANY = "OstLab.uk"
USER_COMPANY_DESC = "Building AI-Powered Solutions, Smart Platforms & Chatbots"
USER_COMPANY_MISSION = "Turning complex challenges into simple, intuitive IT solutions for successful Founders"
USER_COMPANY_FOCUS = "Strategic AI solutions to address complex challenges"
USER_RESPONSIBILITIES = (
    "Strategic Leadership: Oversee the development and implementation of the company’s strategic goals and objectives. "
    "Operational Management: Manage day-to-day operations to ensure the company runs efficiently and effectively. "
    "Financial Oversight: Monitor the company’s financial performance, budgets, and forecasts to ensure financial health and sustainability. "
    "Team Leadership: Lead and mentor the executive team, fostering a culture of collaboration and innovation. "
    "Stakeholder Engagement: Act as the primary liaison between the board of directors, shareholders, and other key stakeholders. "
    "Business Development: Identify and pursue new business opportunities to drive growth and expansion."
)

# class PersonalizedThanksMessage(BaseModel):
#     # Reasoning: Why this message is being sent to this recipient
#     reasoning: str = Field(..., description="Brief reasoning for sending this message (e.g., shared interests, mutual connections, or admiration for their work)." )
#     # Greeting and gratitude
#     greeting: str = Field( ..., description="Brief greeting and thanks for connecting. Please write Hey instead of Hi. ")
#     # Admiration for the recipient’s mission or achievements
#     admiration: str = Field( ..., description="Mention of the recipient’s company mission or achievements.")
#     # Specific mention of technologies or projects
#     specific_mention: str = Field( default="", description="If there is enough information to fill in this field, otherwise leave it empty string. Specific project or technology that impresses you.")
#     # One-sentence introduction to Ostlab company
#     company_intro: str = Field( ..., description="Brief description of OstLab’s mission.")
#     # Connection between IT and their field
#     connection: str = Field( ..., description="How IT complements their work or shared vision.")
#     # Offer to stay in touch
#     stay_in_touch: str = Field(..., description="Polite offer to stay in touch and learn from them.")
#     # Closing gratitude
#     closing: str = Field(..., description="Final thanks and compliment.")
#
# def format_thanks_message(extraction: PersonalizedThanksMessage) -> str:
#     specific_mention = extraction.specific_mention if extraction.specific_mention else ''
#     message_parts = [
#         f"{extraction.greeting}",
#         f"\n{extraction.admiration} {specific_mention}",
#         f"\n{extraction.company_intro} {extraction.connection}",
#         f"\n{extraction.stay_in_touch} {extraction.closing}"
#     ]
#     formatted_message = "\n".join(message_parts)
#     return formatted_message


class PersonalizedThanksMessage(BaseModel):
    reasoning: str = Field(..., description="Brief reasoning for sending this message.")
    holiday_mention: Optional[str] = Field(default=None, description="Mention of a holiday in the recipient's location on the current date, if applicable.")
    message: str = Field(..., description="The full thank-you message text.")

def format_thanks_message(extraction: PersonalizedThanksMessage) -> str:
    formatted_message = extraction.message
    return formatted_message

def generate_personalized_message(row: pd.Series, model,
                                llm_handler: LLMHandler = None) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    recipient_location = row.get("Company location / relevant office", "Unknown")
    company_decr = row['Company Desc'] if 'Company Desc' in row and pd.notna(
        row['Company Desc']) else f"{row.get('Why Relevant Now', '')} \n\n{row.get('Signals', '')}"

    additional_fields = [
        ("Recipient’s Company Size", row.get("Company size")),
        ("Recipient’s Company Location", recipient_location),
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
                f"to draft a personalized LinkedIn thank-you message. "
                "Use **only English** for the message. "
                "Use neutral and less emotionally charged language. "
                f"The message should be on equal terms but warm, friendly, and professional, but not pushy. "
                f"Use fewer compliments (1-2 compliments are enough). "
                f"Use 'Hey' instead of 'Hi' for greeting. "
                f"Make one small grammatical or punctuation mistake to make it sound more natural. "
                f"Be brief!!! "
                f"The message should include the following structure:\n"
                f"   a. Casual greeting and thanks for connecting.\n"
                f"   b. If today is a holiday in the recipient's location, mention it briefly and congratulate them.\n"
                f"   c. Personal admiration for the recipient’s company mission or achievements.\n"
                f"   d. Specific mention of their technologies or projects.\n"
                f"   e. One sentence about {USER_COMPANY}’s mission and your role.\n"
                f"   f. Connection between AI and their field.\n"
                f"   g. Offer to stay in touch and collaborate.\n"
                f"Current date: {current_date}. Recipient's location: {recipient_location}."
            )
        },
        {
            "role": "user",
            "content": (
                f"Draft a LinkedIn thank-you message using the following details:\n\n"
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
                f"- Company Focus: {USER_COMPANY_FOCUS}\n"
                f"- Responsibilities: {USER_RESPONSIBILITIES}"
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

