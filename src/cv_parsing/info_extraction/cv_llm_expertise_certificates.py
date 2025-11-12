import json

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class Certificate(BaseModel):
    name: str = Field(description="Name of the certificate (exact from resume)")
    issuer: Optional[str] = Field(default=None, description="Organization that issued the certificate (exact from resume)")
    date: Optional[str] = Field(default=None, description="Date of certification (exact from resume)")
    link: Optional[str] = Field(default=None, description="Link to the certificate (exact from resume)")

class CertificatesResponse(BaseModel):
    certificates: List[Certificate] = Field(description="List of extracted certificates")

def extract_cv_certificates(
    cv_sections: Dict,
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    """
    Extracts only technical certificates from the resume using a Pydantic model.
    Returns structured certificates, combined text, tokens, and cost.
    """
    certificates_text = get_section_for_field(cv_sections, "Expertise")

    prompt = [
        {
            "role": "system",
            "content": (
                "Extract **only technical certificates** from the resume text. "
                "Ignore non-technical certificates (e.g., language proficiency, soft skills, etc.). "
                "For each technical certificate, provide the name, issuer, date, and link (if available)."
            )
        },
        {
            "role": "user",
            "content": f"Certificates text:\n{certificates_text}"
        }
    ]

    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        response_format=CertificatesResponse,  # Используем обёртку
    )

    certificates = response["parsed"].certificates
    usage = response["usage"]
    cost = response["cost"]["total_cost"]

    combined_text = "\n".join(
        f"- {cert.name} ({cert.issuer}, {cert.date or 'No date'})"
        for cert in certificates
    )

    return {
        "certificates": [cert.model_dump() for cert in certificates],
        "combined_text": combined_text,
        "completion_tokens": usage.completion_tokens,
        "prompt_tokens": usage.prompt_tokens,
        "cost": cost,
    }

