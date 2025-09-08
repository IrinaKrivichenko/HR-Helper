import traceback
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator

from src.nlp.llm_handler import LLMHandler

class LocationExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis for location extraction")
    locations: List[str] = Field(default=[], description="Locations, cities, countries mentioned in resume")
    detected_country: Optional[str] = Field(default=None, description="Primary country detected from resume context")
    current_candidate_country: Optional[str] = Field(default=None, description="Final candidate country with emoji flag, no space")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in extraction")

    @validator("current_candidate_country", pre=True, always=True)
    def format_country_with_emoji(cls, value):
        if not value:
            return None
        # Remove the space between the flag and the country name (if there is one)
        if (len(value) >= 3 and
            all(0x1F1E6 <= ord(c) <= 0x1F1FF for c in value[:2]) and
            value[2] == " "):
            value = value[:2] + value[3:]
        return value


def extract_cv_location(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False) -> dict:
    """
    Extract Location via SGR, focusing on country detection with emoji flags.
    Returns: result dictionary
    """
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert location extractor specializing in resume parsing. "
                "Your task is to identify the country mentioned in the resume. "
                "Follow these rules strictly:\n"
                "1. **Country Name Format**: Return the country name in one word if possible. "
                "If the country name is traditionally two words (e.g., 'United States'), return both words. "
                "Never use abbreviations (e.g., 'USA' is invalid; use 'United States').\n"
                "2. **Emoji Flag**: Prepend the country name with its corresponding emoji flag, WITHOUT a space. "
                # "For example: '🇺🇸United States', '🇷🇺Russia', '🇩🇪Germany'.\n"
                "3. **Detection Rules**:\n"
                "   - Look for explicit mentions of countries (e.g., 'Russia', 'Belarus', 'Germany').\n"
                "   - If only a city is mentioned (e.g., 'Minsk'), infer the country and return only the country with emoji (e.g., '🇧🇾Belarus').\n"
                "   - Ignore company names or ambiguous terms that could be confused with countries.\n"
                "4. **Primary Country**: If multiple countries are mentioned, prioritize the one most likely to be the candidate's current location.\n"
                "5. **No Guessing**: If no country or city is mentioned, return `None` for the country. Do not return an empty string or placeholder.\n"
                "6. **Reasoning**: After identifying possible countries, provide a step-by-step reasoning for selecting the final candidate country."
            )
        },
        {
            "role": "user",
            "content": (
                f"Extract the country from this resume. Follow the rules above strictly.\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    try:
        response = llm_handler.get_answer(
            prompt, model=model, max_tokens=400,
            response_format=LocationExtraction
        )
        extraction = response['parsed']
        cost = response['cost']['total_cost']

        result = {
            "Location": extraction.current_candidate_country if extraction.current_candidate_country else "",
        }
        if "🇧🇾" in result["Location"]:
            result["Location"] = result["Location"].replace("🇧🇾", "🏰", 1)

        if add_tokens_info:
            result.update({
                "Reasoning about Location": "\n".join(extraction.reasoning_steps),
                "Detected Countries": extraction.locations,
                "Model Used": model,
                "Cost": f"${cost:.6f}",
            })
        else:
            result["Cost_of_Location_CV_extraction"] = cost

        return result
    except Exception as e:
        print(f"Location SGR extraction failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {"Location": "", "Cost_of_Location_CV_extraction": 0.0}
