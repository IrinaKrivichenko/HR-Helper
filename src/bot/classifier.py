from pydantic import BaseModel, Field
from typing import Union, Literal, List, Dict, Any

from src.data_processing.nlp.llm_handler import LLMHandler


class VacancyClassification(BaseModel):
    """Model for vacancy classification result."""
    type: Literal["vacancy"] = Field(description="Result type: vacancy.")
    count: int = Field(..., description="Number of vacancies in the text.")

class NamesClassification(BaseModel):
    """Model for names classification result."""
    type: Literal["names"] = Field(description="Result type: names to search.")
    names: List[str] = Field(..., description="List of names extracted from the text.")

class UnknownClassification(BaseModel):
    """Model for unknown classification result."""
    type: Literal["unknown"] = Field(description="Result type: unknown.")

ClassifierResult = Union[VacancyClassification, NamesClassification, UnknownClassification]

class ClassifierResponse(BaseModel):
    """Classifier response model."""
    reasoning: str = Field(..., description="Explanation of why this classification was chosen.")
    result: ClassifierResult
    result_type: Literal["vacancy", "names", "unknown"] = Field(..., description="Type of the result: 'vacancy', 'names', or 'unknown'.")


def parse_llm_classification(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the LLM classification response and returns a structured result.
    Args:
        response (Dict[str, Any]): Raw LLM response.
    Returns:
        Dict[str, Any]: Structured result with 'input_type' and additional data.
    """
    classification_data = response["parsed"]
    result = {}
    if classification_data.result_type == "vacancy":
        result["input_type"] = "vacancy"
        result["count"] = classification_data.result.count
    elif classification_data.result_type == "names":
        result["input_type"] = "names"
        result["names"] = classification_data.result.names
    else:
        result["input_type"] = "unknown"
        result["message"] = "This functionality is not yet implemented. Please contact support."
    return result


def classify_text(text: str, llm_handler: LLMHandler, model: str) -> ClassifierResponse:
    """
    Classifies the input text as a vacancy, names, or unknown using LLM.
    Args:
        text (str): Input text to classify.
        llm_handler (LLMHandler): Handler for LLM interaction.
        model (str): Model name to use for classification.
    Returns:
        ClassifierResponse: Structured classification result.
    """
    # Define the prompt for the LLM
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in classifying texts as either job vacancies, lists of names. "
                "Your task is to analyze the provided text and classify it accordingly."
            )
        },
        {
            "role": "user",
            "content": (
                "Classify the following text:\n\n"
                f"# Text:\n{text}\n\n"
                "1. Determine if the text is a job vacancy, a list of names to find, or something else.\n"
                "2. Provide a brief reasoning for your classification.\n"
                "3. If the text is a list of names, extract the names.\n"
            )
        }
    ]
    # Send the prompt to the LLM and parse the response
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=1000,
        response_format=ClassifierResponse
    )
    # Parse the LLM response
    classification_result = parse_llm_classification(response)
    return classification_result

# Пример использования:
# response_example = {
#     "parsed": {
#         "type": "vacancy",
#         "count": 2,
#         "reasoning": "The text contains two job openings."
#     }
# }
# print(parse_llm_classification(response_example))
