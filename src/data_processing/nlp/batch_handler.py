# https://platform.openai.com/docs/guides/batch

from typing import Optional, Dict, List
from openai import OpenAI
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

class BatchHandler:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI client.
        :param api_key: OpenAI API key. If not provided, it will be taken from the OPENAI_API_KEY environment variable.
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def upload_batch_file(self, file_path: str) -> str:
        """
        Upload a batch input file to OpenAI.
        :param file_path: Path to the .jsonl file with requests.
        :return: ID of the uploaded file.
        """
        with open(file_path, "rb") as file:
            response = self.client.files.create(file=file, purpose="batch")
        return response.id

    def create_batch(self, input_file_id: str, endpoint: str = "/v1/chat/completions") -> str:
        """
        Create a batch for asynchronous processing.
        :param input_file_id: ID of the uploaded file.
        :param endpoint: API endpoint (e.g., "/v1/chat/completions").
        :return: Batch ID.
        """
        batch = self.client.batches.create(
            input_file_id=input_file_id,
            endpoint=endpoint,
            completion_window="24h"
        )
        return batch.id

    def get_batch_status(self, batch_id: str) -> Dict:
        """
        Get the current status of the batch.
        :param batch_id: Batch ID.
        :return: Dictionary with batch status information.
        """
        batch = self.client.batches.retrieve(batch_id)
        return batch.model_dump()

    def wait_for_completion(self, batch_id: str, poll_interval: int = 60) -> None:
        """
        Wait for the batch to complete.
        :param batch_id: Batch ID.
        :param poll_interval: Polling interval in seconds.
        """
        while True:
            status = self.get_batch_status(batch_id)["status"]
            if status == "completed":
                print("Batch completed!")
                break
            elif status == "failed":
                raise RuntimeError(f"Batch {batch_id} failed.")
            print(f"Current status: {status}. Waiting...")
            time.sleep(poll_interval)

    def download_results(self, batch_id: str, output_file_path: str) -> None:
        """
        Download the batch results.
        :param batch_id: Batch ID.
        :param output_file_path: Path to save the results.
        """
        batch = self.get_batch_status(batch_id)
        if batch["status"] != "completed":
            raise ValueError(f"Batch {batch_id} is not completed.")

        output_file_id = batch["output_file_id"]
        if not output_file_id:
            raise ValueError("No output file ID found.")

        content = self.client.files.content(output_file_id).text
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(content)
        print(f"Results saved to {output_file_path}")

    def calculate_batch_cost(
        self,
        model: str,
        input_tokens: int,
        cached_input_tokens: int = 0,
        output_tokens: int = 0
    ) -> float:
        """
        Calculate the cost of running a batch.
        :param model: Model name (e.g., "gpt-4.1-nano").
        :param input_tokens: Number of input tokens.
        :param cached_input_tokens: Number of cached input tokens (if supported).
        :param output_tokens: Number of output tokens.
        :return: Total cost in dollars.
        """
        pricing = {
            "gpt-5": {"input": 0.625, "cached_input": 0.0625, "output": 5.00},
            "gpt-5-mini": {"input": 0.125, "cached_input": 0.0125, "output": 1.00},
            "gpt-5-nano": {"input": 0.025, "cached_input": 0.0025, "output": 0.20},
            "gpt-4.1": {"input": 1.00, "cached_input": 0, "output": 4.00},
            "gpt-4.1-mini": {"input": 0.20, "cached_input": 0, "output": 0.80},
            "gpt-4.1-nano": {"input": 0.05, "cached_input": 0, "output": 0.20},
            "gpt-4o": {"input": 1.25, "cached_input": 0, "output": 5.00},
            "gpt-4o-2024-05-13": {"input": 2.50, "cached_input": 0, "output": 7.50},
            "gpt-4o-mini": {"input": 0.075, "cached_input": 0, "output": 0.30},
            "o4-mini": {"input": 0.55, "cached_input": 0, "output": 2.20},
        }

        if model not in pricing:
            raise ValueError(f"Model {model} not found in pricing table.")

        model_pricing = pricing[model]

        input_cost = (input_tokens * model_pricing["input"]) / 1_000_000
        cached_input_cost = (cached_input_tokens * model_pricing["cached_input"]) / 1_000_000
        output_cost = (output_tokens * model_pricing["output"]) / 1_000_000

        total_cost = input_cost + cached_input_cost + output_cost
        return total_cost

    def calculate_total_tokens(self, results_file_path: str) -> Dict[str, int]:
        """
        Calculate the total number of tokens from the results file.
        :param results_file_path: Path to the results file.
        :return: Dictionary with total input and output tokens.
        """
        total_input_tokens = 0
        total_output_tokens = 0

        with open(results_file_path, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    data = json.loads(line)
                    if "response" in data and data["response"]:
                        body = data["response"]["body"]
                        if "usage" in body:
                            total_input_tokens += body["usage"]["prompt_tokens"]
                            total_output_tokens += body["usage"]["completion_tokens"]
                except json.JSONDecodeError:
                    continue

        return {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }

    def run_batch(
        self,
        input_file_path: str,
        output_file_path: str,
        model: str,
        endpoint: str = "/v1/chat/completions"
    ) -> None:
        """
        Full workflow: upload file, create batch, wait for completion,
        download results, and calculate cost.
        :param input_file_path: Path to the input .jsonl file.
        :param output_file_path: Path to save the results.
        :param model: Model name (e.g., "gpt-4.1-nano").
        :param endpoint: API endpoint.
        """
        print("Uploading batch file...")
        input_file_id = self.upload_batch_file(input_file_path)

        print("Creating batch...")
        batch_id = self.create_batch(input_file_id, endpoint)

        print(f"Batch ID: {batch_id}. Waiting for completion...")
        self.wait_for_completion(batch_id)

        print("Downloading results...")
        self.download_results(batch_id, output_file_path)

        print("Calculating total tokens and cost...")
        tokens = self.calculate_total_tokens(output_file_path)
        total_cost = self.calculate_batch_cost(
            model=model,
            input_tokens=tokens["input_tokens"],
            output_tokens=tokens["output_tokens"]
        )

        print(f"Total input tokens: {tokens['input_tokens']}")
        print(f"Total output tokens: {tokens['output_tokens']}")
        print(f"Total cost: ${total_cost:.4f}")
