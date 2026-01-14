
import time
from typing import Dict, Any

from pydantic import Field, BaseModel

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field, collect_sections_by_keywords
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class CleanedSummaryResponse(BaseModel):
    summary: str = Field(
        ...,
        description="Cleaned resume summary text with removed headers, candidate names, redundant phrases, and informal language."
    )

def extract_cv_cleaned_summary(
    cv_sections: Dict[str, str],
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    start_time = time.time()

    original_summary_text = get_section_for_field(cv_sections, "Summary")

    prompt = [
        {
            "role": "system",
            "content": (
                f"You are a **Professional Resume Editor with a focus on technical precision and confidentiality**. "
                "Your task is to **clean the text** by removing:\n"
                "1. Headers (e.g., 'Summary,' 'About Me', 'About').\n"
                "2. Candidate names (e.g., 'I am John Doe' → remove 'John Doe').\n"
                "3. Redundant phrases, informal language, and excessive details.\n"
                "4. Repetitions that do not add value.\n\n"
                "5. **Logically disconnected fragments** that disrupt the flow or coherence of the summary.\n\n"
                "**Rules:**\n"
                "- Preserve the **original meaning, structure, and technical terms**.\n"
                "- Ensure the **logical flow** of the text. If a phrase or sentence breaks the coherence, remove or adjust it.\n"
                "- Do **not** rewrite or rephrase unless necessary to remove redundancy, informality, or logical inconsistencies.\n"
                "- Do **not** add or remove information unless it is a header, name, redundant detail, or logically disconnected fragment.\n"
                "- The output must be **concise, professional, neutral, and logically consistent**."
            )
        },
        {
            "role": "user",
            "content": (
                f"Please clean the following resume summary according to the rules above:\n\n"
                f"Original Text:\n"
                f"{original_summary_text}"
            )
        }
    ]

    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=max(500, len(original_summary_text)),
        response_format=CleanedSummaryResponse
    )

    cleaned_summary = response["parsed"].summary
    usage = response["usage"]
    cost = response["cost"]["total_cost"]

    return {
        "Cleaned Summary": cleaned_summary,
        "Model of_cleaning_summary_in_CV_extraction": model,
        "Completion_tokens of_cleaning_summary_in_CV_extraction": usage.completion_tokens,
        "Prompt_tokens of_cleaning_summary_in_CV_extraction": usage.prompt_tokens,
        "Cost of_cleaning_summary_in_CV_extraction": cost,
        "Time": time.time() - start_time,
    }

