from typing import List, Dict
from openai import OpenAI, AuthenticationError, OpenAIError
from dotenv import load_dotenv
import os
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


    def get_answer(self, prompt: List[Dict[str, str]], model="gpt-4o-mini", max_tokens=200, temperature=0, seed=42):
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        )
        answer = response.choices[0].message.content
        return answer

