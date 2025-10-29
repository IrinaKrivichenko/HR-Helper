import json
import time
import traceback
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, validator

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.countries_info import CountryFlag
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class LocationExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis for location extraction")
    locations: List[str] = Field(default=[], description="Locations, cities, countries mentioned in resume")
    detected_country: Optional[str] = Field(default=None, description="Primary country detected from resume context")
    current_candidate_country: CountryFlag = Field(description="Final candidate country with emoji flag, no space")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in extraction")

def extract_cv_location(
        cv_sections: Dict,
        llm_handler: LLMHandler,
        model: str = "gpt-4.1-nano"
) -> dict:
    """
    Extract Location via SGR, focusing on country detection with emoji flags.
    Returns: result dictionary
    """
    start_time = time.time()
    cv = get_section_for_field(cv_sections, "Location")
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
                "3. **Detection Rules**:\n"
                "   - Look for explicit mentions of countries.\n"
                "   - If only a city is mentioned, infer the country and return only the country with emoji.\n"
                "   - Ignore company names or ambiguous terms that could be confused with countries.\n"
                "   - **Current Country Priority**: The candidate's current country is most likely mentioned at the very beginning or at the very end of the resume.\n"
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
            prompt,
            model=model,
            max_tokens=400,
            response_format=LocationExtraction
        )

        extraction = response['parsed']
        usage = response['usage']
        cost_info = response['cost']

        # Format main location field
        location_value = extraction.current_candidate_country if extraction.current_candidate_country else ""
        if location_value.startswith("NO"):
            location_value = ""
        elif "🇧🇾" in location_value: # Replace Belarus flag if needed
            location_value = location_value.replace("🇧🇾", "🏰", 1)

        # Build result dictionary with all fields
        result = {
            "Location": location_value,
            "Reasoning about Location": "\n".join(f"• {step}" for step in extraction.reasoning_steps),
            "Detected Countries": ", ".join(extraction.locations) if extraction.locations else "",
            "Model of_Location_CV_extraction": model,
            "Completion Tokens of_Location_CV_extraction": str(usage.completion_tokens),
            "Prompt Tokens _of_Location_CV_extraction": str(usage.prompt_tokens),
            "Cost_of_Location_CV_extraction": cost_info['total_cost'],
            "Confidence_Location": extraction.confidence,
            "Time" : time.time()-start_time,
        }

        # Log the complete response in a single entry
        logger.info(
            f"Field extraction completed - Field: 'Location' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(f"Location SGR extraction failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Build error result dictionary
        result = {
            "Location": "",
            "Reasoning about Location": f"Extraction failed: {e}",
            "Detected Countries": "",
            "Model of_Location_CV_extraction": model,
            "Completion Tokens of_Location_CV_extraction": "0",
            "Prompt Tokens _of_Location_CV_extraction": "0",
            "Cost_of_Location_CV_extraction": 0.0,
            "Confidence_Location": "low",
            "Time" : time.time()-start_time,
        }

        # Log the error response
        logger.info(
            f"Field extraction completed - Field: 'Location' | Response: {json.dumps(result, ensure_ascii=False)}")

        return result


