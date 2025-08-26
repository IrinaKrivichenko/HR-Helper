from pydantic import BaseModel, Field
from typing import List, Literal

from src.nlp.llm_handler import extract_and_parse_token_section, LLMHandler


class CVSeniorityAnalysis(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis in bullet points")
    seniority_level: Literal["Junior", "Middle", "Senior", "Principle", "Could not determine"] = Field(
        description="Final seniority classification"
    )


def extract_cv_seniority(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Extract CV seniority level using Schema-Guided Reasoning approach.
    """

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a senior technical recruiter with strict criteria for evaluating seniority levels. "
                "You MUST respond with valid JSON only, no additional text, markdown, or formatting."
            )
        },
        {
            "role": "user",
            "content": (
                f"Analyze this resume to determine the candidate's seniority level using the strict decision tree.\n\n"
                f"**Decision Tree:**\n"
                f"1. **Principle:** 10+ years relevant IT/Data Science experience AND executive titles (CTO, VP, Director)\n"
                f"2. **Senior:** 5+ years experience AND 'Senior' title AND mentoring/architectural responsibilities\n"
                f"3. **Middle:** 2-5 years experience AND independent work with minimal supervision\n"
                f"4. **Junior:** Default if none above are met\n\n"
                f"**Rules:**\n"
                f"- Only count IT/Data Science roles as relevant experience\n"
                f"- Executive titles required for Principle (project leadership ≠ executive)\n"
                f"- If insufficient evidence, use 'Could not determine'\n\n"
                f"Respond ONLY with this JSON structure:\n"
                f"{{\n"
                f'  "reasoning_steps": ["Candidate has 7 years of relevant experience", "Holds Senior Data Scientist title"],\n'
                f'  "seniority_level": "Senior"\n'
                f"}}\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    # Calculate max tokens based on CV length
    max_tokens = len(cv)

    # Get response from LLM
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    if not response:
        return {"Seniority": "Could not determine", "Cost_of_Seniority_CV_extraction": 0}

    print(response)  # Debug print

    # Extract and parse token section
    cleaned_response, token_data = extract_and_parse_token_section(
        response=response,
        additional_key_text="",
        add_tokens_info=add_tokens_info
    )

    # Parse JSON response
    try:
        import json

        # Clean the response
        cleaned_response = cleaned_response.strip()

        # Remove markdown code blocks if present
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]

        cleaned_response = cleaned_response.strip()

        if not cleaned_response:
            return _fallback_cv_seniority_parse(response, token_data, add_tokens_info)

        parsed_data = json.loads(cleaned_response)

        # Validate with Pydantic
        seniority_analysis = CVSeniorityAnalysis(**parsed_data)

    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON parsing failed: {e}")
        return _fallback_cv_seniority_parse(response, token_data, add_tokens_info)

    # Build result dictionary
    result = {}

    if add_tokens_info:
        result["Reasoning about Seniority"] = "\n".join([f"• {step}" for step in seniority_analysis.reasoning_steps])
        result.update(token_data)

    # Set seniority level
    result["Seniority"] = seniority_analysis.seniority_level

    # Add cost info
    if "Cost" in token_data:
        if not add_tokens_info:
            cost = float(token_data["Cost"].replace("$", ""))
            result["Cost_of_Seniority_CV_extraction"] = cost

    return result


def _fallback_cv_seniority_parse(response: str, token_data: dict, add_tokens_info: bool) -> dict:
    """
    Fallback parser for CV seniority extraction when JSON parsing fails.
    """
    result = {}

    if add_tokens_info:
        result["Reasoning about Seniority"] = "Unable to extract reasoning from response"
        result.update(token_data)

    # Try to extract seniority from response text
    seniority_levels = ["Junior", "Middle", "Senior", "Principle", "Could not determine"]
    found_seniority = "Could not determine"

    for level in seniority_levels:
        if level in response:
            found_seniority = level
            break

    result["Seniority"] = found_seniority

    if "Cost" in token_data and not add_tokens_info:
        cost = float(token_data["Cost"].replace("$", ""))
        result["Cost_of_Seniority_CV_extraction"] = cost

    return result

