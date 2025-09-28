"""
Full section extraction with proper field descriptions.
"""
import time
from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field
from src.logger import logger

class HeaderSection(BaseModel):
    section: Literal["header"]
    found: bool = Field(description="True if header section with name and contacts exists")
    content: str = Field(description="Full text of header including name, email, phone, LinkedIn, location")

class SummarySection(BaseModel):
    section: Literal["summary"]
    found: bool = Field(description="True if professional summary/objective exists")
    content: str = Field(description="Complete professional summary or objective text, empty if not found")

class SkillsSection(BaseModel):
    section: Literal["skills"]
    found: bool = Field(description="True if skills section exists")
    content: str = Field(description="All technical skills, programming languages, tools, frameworks listed")

class ExperienceSection(BaseModel):
    section: Literal["experience"]
    found: bool = Field(description="True if work experience section exists")
    content: str = Field(description="Complete work history including jobs, projects, internships")

class EducationSection(BaseModel):
    section: Literal["education"]
    found: bool = Field(description="True if education section exists")
    content: str = Field(description="All education, degrees, certifications, courses, academic publications")

class FullSectionsSchema(BaseModel):
    overall_reasoning: str = Field(
        description="Your initial analysis of resume structure and how you'll extract sections"
    )
    section_reasoning: str = Field(
        default="",
        description="Your reasoning about how to handle any additional sections not covered by standard fields. "
    )
    header: HeaderSection = Field(
        description="Header section with contact information at the top of resume"
    )
    summary: SummarySection = Field(
        description="Professional summary or objective statement if present"
    )
    skills: SkillsSection = Field(
        description="Technical and soft skills section"
    )
    experience: ExperienceSection = Field(
        description="Work experience, employment history, projects"
    )
    education: EducationSection = Field(
        description="Educational background, degrees, certifications, publications"
    )

def extract_full_sections(cv_text: str, llm_handler: Any, model: str) -> Dict[str, Any]:
    """Extract all sections with initial reasoning and validation."""
    start_time = time.time()
    prompt = [
        {
            "role": "system",
            "content": (
                "You are a resume parser. First analyze, then extract sections.\n"
                "Rules:\n"
                "1. FIRST provide overall_reasoning - your thoughts on resume structure and extraction approach\n"
                "2. For each standard section, set found=true if it exists, found=false if not\n"
                "3. If section not found, set content to empty string ''\n"
                "4. If section found, copy its COMPLETE text exactly as it appears\n"
                "5. If you find any text that doesn't fit standard sections, provide section_reasoning about where it might belong\n"
                "6. The goal is to capture 100% of the resume text across all sections"
            )
        },
        {
            "role": "user",
            "content": f"Analyze and extract all sections from this resume:\n\n{cv_text}"
        }
    ]
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=min(len(cv_text) * 2, 8000),
        response_format=FullSectionsSchema
    )
    # Extract from structured response
    extraction = response['parsed']
    usage = response.get('usage')
    cost_info = response.get('cost', {})

    # Build sections dictionary
    sections = {}
    for field in ['header', 'summary', 'skills', 'experience', 'education']:
        section = getattr(extraction, field)
        if section.found and section.content:
            sections[field.capitalize()] = section.content

    # Validate the extraction
    validation = validate_full_sections_extraction(cv_text, sections)

    # Extract token information correctly
    prompt_tokens = usage.prompt_tokens if usage and hasattr(usage, 'prompt_tokens') else 0
    completion_tokens = usage.completion_tokens if usage and hasattr(usage, 'completion_tokens') else 0

    return {
        "sections": sections,
        "reasoning": extraction.overall_reasoning + "\n\n" + extraction.section_reasoning,
        "validation": validation,
        "method": "full",
        "cost": cost_info.get('total_cost', 0),
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        },
        "time": time.time() - start_time
    }

def validate_full_sections_extraction(original_text: str, sections: Dict[str, str]) -> Dict[str, Any]:
    """Validate that sections cover 95%+ of original text."""
    original_words = set(original_text.lower().split())
    extracted_words = set(" ".join(sections.values()).lower().split())
    intersection = len(original_words & extracted_words)
    union = len(original_words | extracted_words)
    jaccard = intersection / union if union > 0 else 0
    coverage_percent = jaccard * 100
    passed = jaccard >= 0.95
    return {
        "is_valid": passed,
        "method": "full",
        "issues": [] if passed else [f"Coverage {coverage_percent:.1f}% < 95%"],
        "metrics": {
            "jaccard": jaccard,
            "coverage_percent": coverage_percent,
            "threshold_met": passed,
            "sections_found": len(sections)
        },
        "summary": f"Coverage: {coverage_percent:.1f}%, Threshold {'met' if passed else 'not met'}"
    }
