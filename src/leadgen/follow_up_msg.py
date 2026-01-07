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
# class FollowUpMessage(BaseModel):
#     greeting: str = Field(..., description="Casual greeting and well-wishing. Please write Hey instead of Hi.")
#     connection_mention: str = Field(..., description="Mention of previous connection.")
#     interest_question: str = Field(..., description="Question or interest in their work, challenges, or experience.")
#     stay_in_touch: str = Field(..., description="Offer to stay in touch and potential collaboration. Use word 'nice'")

class FollowUpMessage(BaseModel):
    reasoning: str = Field(..., description="Brief reasoning for sending this message.")
    holiday_mention: Optional[str] = Field(default=None, description="Mention of a holiday in the recipient's location on the current date, if applicable.")
    message: str = Field(..., description="The full follow-up message text.")

def format_follow_up_message(extraction: FollowUpMessage) -> str:
    # message_parts = [
    #     f"{extraction.greeting}",
    #     f"\n{extraction.connection_mention} {extraction.interest_question}",
    #     f"\n{extraction.stay_in_touch}"
    # ]
    # formatted_message = "\n".join(message_parts)
    formatted_message = extraction.message
    return formatted_message

# def extract_years_since_founded(founded_str: str) -> Optional[int]:
#     try:
#         year = None
#         for word in founded_str.split():
#             if word.isdigit() and len(word) == 4:
#                 year = int(word)
#                 break
#         if year is not None:
#             current_year = datetime.now().year
#             return current_year - year
#     except:
#         pass
#     return None

def generate_follow_up_message(row: pd.Series, model,
                                llm_handler: LLMHandler = None) -> str:
    company_decr = row['Company Desc'] if row['Company Desc'] else f"{row['Why Relevant Now']} \n\n{row['Signals']}"
    recipient_location = f"Recipient's location: {row['Company location / relevant office']}." if row['Company location / relevant office'] else ""
    current_date = datetime.now().strftime("%Y-%m-%d")

    additional_fields = [
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
                "Use **only English** for the message. "
                "Use neutral and less emotionally charged language."
                f"The message should be on equal terms but warm, friendly, and professional, but not pushy. "
                f"Use fewer compliments (1-2 compliments are enough). "
                f"Make one small grammatical or punctuation mistake to make it sound more natural. "
                f"Ask about their challenges, tools, or ways they use AI, depending on the information about their company. "
                f"Be brief!!!"
                f"The message should include the following structure:\n"
                f"   a. Casual greeting and well-wishing.\n"
                f"   b. If today is a holiday in the recipient's location, mention it briefly and congratulate them.\n"
                f"   c. Mention of previous connection.\n"
                f"   d. Question or interest in their work, challenges, tools, or ways they use AI.\n"
                f"   e. Offer to stay in touch and potential collaboration.\n"
                f"Current date: {current_date}. {recipient_location}"
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
                f"- Company Focus: {USER_COMPANY_FOCUS}\n"
                f"- Responsibilities: {USER_RESPONSIBILITIES}\n\n"
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
