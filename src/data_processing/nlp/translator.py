from typing import Dict
from langdetect import detect, LangDetectException
from langcodes import Language

from src.data_processing.nlp.llm_handler import LLMHandler, extract_and_parse_token_section


def parse_llm_translate_text_response(response: str) -> Dict[str, str]:
    response, _ = extract_and_parse_token_section(response=response)
    extracted_data = {'text': response}
    return extracted_data

def translate_text_with_llm(text, llm_handler=None, model="gpt-4.1-nano"):
    if llm_handler is None:
        llm_handler = LLMHandler()
    original_language = None
    try:
        # Detect the language of the input text
        lang_code = detect(text)
        original_language = Language.get(lang_code).display_name()
    except LangDetectException:
        # If language detection fails, set to "Unknown"
        original_language = "Unknown"

    # If the text is already in English, return it as-is
    if original_language == "English":
        return {
            'text': text,
            'original_language': original_language,
        }

    prompt = [
        {
            "role": "system",
            "content": "You are a helpful assistant that translates text to English. Translate the following text to English, leaving any non-textual characters unchanged and do not add any additional text."
        },
        {
            "role": "user",
            "content": f"Translate the following text to English:\n\n{text}"
        }
    ]

    answer = llm_handler.get_answer(prompt, model, max_tokens=len(text) )

    result = parse_llm_translate_text_response(answer)
    result['original_language'] = original_language

    return result