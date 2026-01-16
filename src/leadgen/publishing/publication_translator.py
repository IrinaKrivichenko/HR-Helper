from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from src.data_processing.nlp.llm_handler import LLMHandler

class TranslationAndClassificationResult(BaseModel):
    translated_text: str = Field(..., description="Translated text in English.")
    reasoning: str = Field(..., description="Reasoning for the classification.")
    classification: Literal["generally broad", "specifically related to some industry"] = Field(..., description="Classification of the text.")

def translate_and_classify_post(
    text: str,
    model: str,
    llm_handler: Optional[LLMHandler] = None
) -> Dict[str, str]:
    """
    Translate text into English and classify it as 'generally broad' or 'specifically related to some industry'.
    Args:
        text: Source text to translate and classify.
        model: Model to use for translation and classification.
        llm_handler: An LLMHandler instance for interacting with the model.
    Returns:
        Dict[str, str]: Dictionary with translated text, reasoning, and classification.
    """
    if llm_handler is None:
        llm_handler = LLMHandler()

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a professional translator and analyst. "
                "1. Translate the following text into English. "
                "2. Provide concise reasoning for the classification. "
                "3. Classify the text as either 'generally broad' or 'specifically related to some industry'. "
                "Return the result in JSON format with keys: 'translated_text', 'reasoning', and 'classification'."
            )
        },
        {
            "role": "user",
            "content": text
        }
    ]

    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=1000,
        temperature=0.2,
        response_format=TranslationAndClassificationResult
    )

    result = {
        "translated_text": response["parsed"].translated_text,
        "reasoning": response["parsed"].reasoning,
        "classification": response["parsed"].classification
    }

    return result

