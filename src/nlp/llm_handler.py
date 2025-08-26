from typing import List, Dict
from openai import OpenAI, AuthenticationError, OpenAIError
from dotenv import load_dotenv
import os

from src.logger import logger

load_dotenv()

class LLMHandler:
    def __init__(self, api_key=None, url=None):
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        if url is None:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = OpenAI(api_key=api_key, base_url=url)
        # self.GENERATIVE_MODEL = model
        self.MAX_TOKENS_BY_MODEL = {
            "gpt-4o-mini": 16384,
            # Для остальных моделей можно добавить ограничения здесь
            # Например:
            # "gpt-4.1-mini": 8192,
            # "gpt-4.1-nano": 4096,
            # "gpt-5-mini": 32768,
            # "gpt-5-nano": 16384,
        }

    def calculate_cost(self, token_usage, model):
        # Define pricing for the models
        pricing = {
            "gpt-4.1-mini": {
                "input_price": 0.40,
                "cached_input_price": 0.10,
                "output_price": 1.60
            },
            "gpt-4o-mini": {
                "input_price": 0.15,
                "cached_input_price": 0.075,
                "output_price": 0.60
            },
            "gpt-4.1-nano": {
                "input_price": 0.10,
                "cached_input_price": 0.025,
                "output_price": 0.40
            },
            "gpt-5-mini": {
                "input_price": 0.25,
                "cached_input_price": 0.025,
                "output_price": 2.00
            },
            "gpt-5-nano": {
                "input_price": 0.05,
                "cached_input_price": 0.005,
                "output_price": 0.40
            }

        }

        # Determine the base model name
        base_model = next((key for key in pricing.keys() if model.startswith(key)), None)
        if base_model is None:
            return {
                "input_cost": 0,
                "cached_input_cost": 0,
                "output_cost": 0,
                "total_cost": 0
            }

        # Calculate cost based on token usage
        input_cost = (token_usage.prompt_tokens - token_usage.prompt_tokens_details.cached_tokens) * \
                     pricing[base_model]["input_price"] / 1_000_000
        cached_input_cost = token_usage.prompt_tokens_details.cached_tokens * pricing[base_model][
            "cached_input_price"] / 1_000_000
        output_cost = token_usage.completion_tokens * pricing[base_model]["output_price"] / 1_000_000
        total_cost = input_cost + cached_input_cost + output_cost

        return {
            "input_cost": input_cost,
            "cached_input_cost": cached_input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    def get_answer(self, prompt: List[Dict[str, str]], model="gpt-4.1-nano",
                   max_tokens=1000, temperature=0, seed=42):
        try:
            prompt_text = str(prompt)
            # Define parameters based on the model
            completion_params = {
                "model": model,
                "messages": prompt,
                "temperature": temperature,
                "seed": seed,
            }

            # Add the appropriate max tokens parameter based on the model
            if model in self.MAX_TOKENS_BY_MODEL:
                max_tokens = min(max_tokens, self.MAX_TOKENS_BY_MODEL[model])
            if model in ["gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o-mini"]:
                completion_params["max_tokens"] = max_tokens
            else:
                completion_params["max_completion_tokens"] = max_tokens

            response = self.openai_client.chat.completions.create(**completion_params)

            answer = response.choices[0].message.content
            token_usage = response.usage

            # Calculate cost
            cost = self.calculate_cost(token_usage, model)

            # Append token usage and cost information to the answer
            cached_tokens = token_usage.prompt_tokens_details.cached_tokens if hasattr(token_usage,
                                                                                       'prompt_tokens_details') and hasattr(
                token_usage.prompt_tokens_details, 'cached_tokens') else 0
            token_info = (
                f"\n\n## Token Usage and Cost:\n"                
                f" - Model Used: {model}\n"
                f" - Completion Tokens: {token_usage.completion_tokens}\n"
                f" - Prompt Tokens: {token_usage.prompt_tokens}\n"
                f" - Cached Tokens: {cached_tokens}\n"
                f" - Cost: ${cost['total_cost']:.6f}"
            )
            answer += token_info
            return answer

        except Exception as e:
            logger.error(f"An error occurred while getting the answer from model {model}: {e}")
            return None

def parse_token_usage_and_cost(section_content: str,
                               additional_key_text: str='',
                               add_tokens_info: bool=False) -> dict:
    """
    Parses token usage and cost information from a given text section.
    Args:
    - section_content (str): The text section containing token usage and cost information.
    - additional_key_text (str): Additional text to customize the dictionary keys.
    - add_tokens_info (bool): Whether to include detailed token information or just the total cost.
    Returns:
    - dict: A dictionary containing the parsed token usage and cost information.
    """
    extracted_data = {}

    # Parse each line and store specific fields
    lines = section_content.split('\n')
    if add_tokens_info:
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().strip('- ')
                value = value.replace('$', '').strip()

                # Only include specific fields if add_tokens_info is True
                if key in ["Model Used", "Completion Tokens", "Prompt Tokens", "Cached Tokens", "Cost"]:
                    full_key = f"{key}{additional_key_text}"
                    extracted_data[full_key] = value
    else:
        # Only store the Total Cost information
        for line in lines:
            if "Model Used" in line:
                value = line.split(':', 1)[1].strip()
                full_key = f"Model Used{additional_key_text}"
                extracted_data[full_key] = value
            elif "Cost" in line:
                value = line.split(':', 1)[1].replace('$', '').strip()
                full_key = f"Cost{additional_key_text}"
                extracted_data[full_key] = value
    return extracted_data

def extract_and_parse_token_section(
    response: str,
    additional_key_text: str = '',
    add_tokens_info: bool = False
) -> tuple[str, dict]:
    """
    Extracts and parses the "## Token Usage and Cost:" section from the model's response.
    Returns the cleaned response (without the token section) and a dictionary with token/cost data.

    Args:
        response (str): Full model response, including the token usage section.
        additional_key_text (str): Additional text to customize dictionary keys (e.g., " candidates_selection").
        add_tokens_info (bool): Whether to include detailed token info or just the total cost.

    Returns:
        tuple[str, dict]:
            - Cleaned response (without the token section).
            - Dictionary with parsed token usage and cost data.
    """
    # Find the start of the token usage section
    token_section_start = response.find("## Token Usage and Cost:")

    if token_section_start == -1:
        # If no token section is found, return the original response and an empty dict
        return response, {}

    # Extract the token section
    token_section = response[token_section_start:]
    # Parse token usage and cost information
    token_data = parse_token_usage_and_cost(
        section_content=token_section,
        additional_key_text=additional_key_text,
        add_tokens_info=add_tokens_info
    )
    # Remove the token section from the response
    cleaned_response = response[:token_section_start].strip()

    return cleaned_response, token_data

