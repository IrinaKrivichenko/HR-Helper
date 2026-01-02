import pandas as pd

from src.data_processing.date_parser import days_since
from src.data_processing.nlp.llm_handler import LLMHandler
from src.leadgen.follow_up_msg import generate_follow_up_message
from src.leadgen.leadgen_utils import replace_text_with_dict
from src.leadgen.thnx_personalized_msg import generate_personalized_message


def generate_generic_message(row: pd.Series):
    message = f"""Thanks for connecting, {row['First Name']}- it’s always beneficial to build up our network and stay in touch.

Always happy to exchange ideas or make an intro if it’s helpful. And if anything on my profile catches your eye, feel free to ping me anytime.

Curious, are you a company owner, or more on the product/tech side? What kind of software are you working on?
"""
    return message


def generate_thnx_for_connection_msg(row: pd.Series) -> list[str]:
    # Проверяем обязательные поля
    required_fields = ["First Name", "Company Name"]
    if any(row[field].strip() == "" for field in required_fields):
        return [generate_generic_message(row)]
    else:
        llm_handler = LLMHandler()
        if days_since(row['Datetime of the last touch Andrus'])<14:
            messages = [generate_personalized_message(row, tone="friendly", llm_handler=llm_handler, model="gpt-4.1")]
        else:
            messages = [generate_follow_up_message(row, tone="friendly", llm_handler=llm_handler, model="gpt-4.1")]
        return [replace_text_with_dict(msg) for msg in messages]