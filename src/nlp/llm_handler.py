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


    def calculate_cost(self, token_usage, model="gpt-4.1-mini"):
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
        input_cost = (token_usage.prompt_tokens - token_usage.prompt_tokens_details.cached_tokens) * pricing[base_model]["input_price"] / 1_000_000
        cached_input_cost = token_usage.prompt_tokens_details.cached_tokens * pricing[base_model]["cached_input_price"] / 1_000_000
        output_cost = token_usage.completion_tokens * pricing[base_model]["output_price"] / 1_000_000

        total_cost = input_cost + cached_input_cost + output_cost

        return {
            "input_cost": input_cost,
            "cached_input_cost": cached_input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

    def get_answer(self, prompt: List[Dict[str, str]], model="gpt-4.1-mini", max_tokens=200, temperature=0, seed=42):
        try:
            # Extract the first and last 50 characters of the prompt
            prompt_text = str(prompt)
            first_50_chars = prompt_text[:50]
            last_50_chars = prompt_text[-50:]

            response = self.openai_client.chat.completions.create(
                model=model,
                messages=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
            )

            answer = response.choices[0].message.content
            token_usage = response.usage

            # Calculate cost
            cost = self.calculate_cost(token_usage, model)

            # Log token usage information and prompt snippets in a single log entry
            cached_tokens = token_usage.prompt_tokens_details.cached_tokens if hasattr(token_usage,
                                                                                       'prompt_tokens_details') and hasattr(
                token_usage.prompt_tokens_details, 'cached_tokens') else 0
            logger.info(
                f"Token Usage - Completion Tokens: {token_usage.completion_tokens}, "
                f"Prompt Tokens: {token_usage.prompt_tokens}, "
                f"Total Tokens: {token_usage.total_tokens}, "
                f"Cached Tokens: {cached_tokens}. "
                f"Prompt Preview - First 50: {first_50_chars}, "
                f"Last 50: {last_50_chars}. "
                f"Cost - Input: ${cost['input_cost']:.6f}, "
                f"Cached Input: ${cost['cached_input_cost']:.6f}, "
                f"Output: ${cost['output_cost']:.6f}, "
                f"Total: ${cost['total_cost']:.6f}"
            )
            return answer
        except Exception as e:
            logger.error(f"An error occurred while getting the answer: {e}")
            return None


