import pandas as pd
from pydantic import BaseModel, Field
from typing import Optional, Literal
from annotated_types import MaxLen

# Constants for the user (Andrus)
USER_FIRST_NAME = "Andrus"
USER_POSITION = "CEO & Co-Founder"
USER_COMPANY = "OstLab"
USER_COMPANY_DESC = "AI-driven solutions for businesses"
USER_COMPANY_MISSION = "help businesses leverage artificial intelligence to enhance operations and achieve goals"
USER_COMPANY_FOCUS = "developing and implementing tailored AI solutions"
USER_TEAM_DESC = "experts in AI, data science, and machine learning"
USER_LINKEDIN_PROFILE = "linkedin.com/in/andrus"  # Замени на реальную ссылку


class PersonalizedMessage(BaseModel):
    # Reasoning: Why this message is being sent to this recipient
    reasoning: str = Field(..., max_length=350, description="Brief reasoning for sending this message (e.g., shared interests, mutual connections, or admiration for their work)." )
    # Greeting and gratitude
    greeting: str = Field( ..., max_length=50, description="Brief greeting and thanks for connecting.")
    # Admiration for the recipient’s mission or achievements
    admiration: str = Field( ..., max_length=120, description="Mention of the recipient’s company mission or achievements.")
    # Specific mention of technologies or projects
    specific_mention: str = Field( ..., max_length=100, description="Specific project or technology that impresses you.")
    # One-sentence introduction to your company
    company_intro: str = Field( ..., max_length=160, description="Brief description of OstLab’s mission.")
    # Connection between IT and their field
    connection: str = Field( ..., max_length=100, description="How IT complements their work or shared vision.")
    # Offer to stay in touch
    stay_in_touch: str = Field(..., max_length=80, description="Polite offer to stay in touch and learn from them.")
    # Closing gratitude
    closing: str = Field(..., max_length=50, description="Final thanks and compliment.")


def generate_generic_message():
    pass

def generate_personalized_message(row):
    pass


# "Recipient’s Company Name",	"Recipient’s Company Founded Year",	"Recipient’s Company size", "Recipient’s Company location / relevant office",	"Recipient’s Company Motto",	"Recipient’s Company Desc"

def generate_thnx_for_connection_msg(row: pd.Series) -> str:
    # Проверяем обязательные поля
    required_fields = ["First Name", "Company Name", "Company Desc"]
    if any(row[field].strip() == "" for field in required_fields):
        return generate_generic_message()
    else:
        return generate_personalized_message(row)