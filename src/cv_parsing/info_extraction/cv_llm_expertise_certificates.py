
import time
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from src.cv_parsing.info_extraction.prepare_cv_sections import get_section_for_field, collect_sections_by_keywords
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger  # Added logger import


class Certificate(BaseModel):
    name: str = Field(description="Name of the certificate (exact from resume)")
    issuer: Optional[str] = Field(default=None, description="Organization that issued the certificate (exact from resume)")
    date: Optional[str] = Field(default=None, description="Date of certification (exact from resume)")
    link: Optional[str] = Field(default=None, description="Link to the certificate (exact from resume)")

class Award(BaseModel):
    title: str = Field(description="Award or honor name (exact from resume)")
    issuer: Optional[str] = Field(default=None, description="Organization/event that granted the award (exact from resume)")
    date: Optional[str] = Field(default=None, description="Date or year of the award (exact from resume)")
    description: Optional[str] = Field(default=None, description="Short description or reason (exact from resume)")
    link: Optional[str] = Field(default=None, description="Link to the award page (exact from resume)")

class CertificatesAndAwardsResponse(BaseModel):
    certificates: List[Certificate] = Field(default_factory=list, description="List of extracted certificates")
    awards: List[Award] = Field(default_factory=list, description="List of extracted awards and honors")

CERT_CONTENT_KWS = [
    "cert", "certification", "certifications", "license", "licenses",
    "training", "courses", "course", "professional development", "development",
    "accreditation", "accreditations",
    "certified", "aws", "gcp", "azure", "microsoft certified", "oracle", "google cloud",
    "cka", "ckad", "ckss", "pmp", "scrum", "itil", "comptia", "az-", "dp-", "pl-", "sc-",
]

AWARD_CONTENT_KWS = [
    "award", "awards", "honor", "honors", "prize", "prizes", "distinction",
    "recognition", "achievement", "achievements", "accomplishment", "accomplishments",
    "merit", "laureate",
    "winner", "finalist", "best", "top", "1st place", "2nd place", "3rd place",
]


def extract_cv_certificates_and_awards(
    cv_sections: Dict[str, str],
    llm_handler: LLMHandler,
    model: str = "gpt-4.1-nano"
) -> Dict[str, Any]:
    start_time = time.time()


    certificates_text = collect_sections_by_keywords(
        cv_sections,
        name_keywords=[],
        content_keywords=CERT_CONTENT_KWS,
    )
    awards_text = collect_sections_by_keywords(
        cv_sections,
        name_keywords=[],
        content_keywords=AWARD_CONTENT_KWS,
    )

    # Нет релевантного текста — не вызываем LLM
    if not certificates_text and not awards_text:
        logger.info("No certificate/award-related text found. Skipping LLM call.")
        return {
            "Certificates": "",
            "Awards": "",
            "Model of_Certificates_and_Awards_CV_extraction": model,
            "Completion_tokens of_Certificates_and_Awards_CV_extraction": 0,
            "Prompt_tokens of_Certificates_and_Awards_CV_extraction": 0,
            "Cost of_Certificates_and_Awards_CV_extraction": 0.0,
            "Time": time.time() - start_time,
        }

    combined_input = (
        f"Certificates-related text:\n{certificates_text}\n\n"
        f"Awards-related text:\n{awards_text}"
    ).strip()

    prompt = [
        {
            "role": "system",
            "content": (
                "Extract the following from the resume text:\n"
                "1) ONLY technical certificates (ignore language proficiency, soft skills, participation without certification).\n"
                "2) Awards/Honors/Prizes/Distinctions (exclude generic participation without an award).\n"
                "Use exact wording from the resume for fields.\n"
                "Return two structured lists: certificates and awards."
            )
        },
        {"role": "user", "content": combined_input}
    ]

    response = llm_handler.get_answer(
        prompt=prompt,
        model=model,
        max_tokens=3077,
        response_format=CertificatesAndAwardsResponse,
    )

    parsed = response["parsed"]
    certificates = parsed.certificates or []
    awards = parsed.awards or []

    usage = response["usage"]
    cost = response["cost"]["total_cost"]

    certificates_text_out = "\n".join(f"- {cert.name}" for cert in certificates) if certificates else ""
    awards_text_out = "\n".join(f"- {award.title}" for award in awards) if awards else ""

    return {
        "Certificates": certificates_text_out,
        "Awards": awards_text_out,
        "Model of_Certificates_and_Awards_CV_extraction": model,
        "Completion_tokens of_Certificates_and_Awards_CV_extraction": usage.completion_tokens,
        "Prompt_tokens of_Certificates_and_Awards_CV_extraction": usage.prompt_tokens,
        "Cost of_Certificates_and_Awards_CV_extraction": cost,
        "Time": time.time() - start_time,
    }

