"""
Full section extraction with proper field descriptions.
"""
import time
from typing import Dict, Any, List, Literal, Annotated, Optional
from pydantic import BaseModel, Field
from annotated_types import MinLen
from difflib import SequenceMatcher

from src.cv_parsing.sections.section_by_section import MANDATORY_SECTIONS
from src.data_processing.nlp.llm_handler import LLMHandler


class FragmentClassification(BaseModel):
    fragment: str = Field(description="Original text of the resume fragment")
    reason: str = Field(
        description="Brief explanation (1 sentence) of why this fragment belongs to the chosen section"
    )
    section: Literal["header", "summary", "skills", "experience", "education"] = Field(
        description=(
            "Section to which this fragment belongs. "
            "header: name, contacts, location; "
            "summary: professional summary or objective; "
            "skills: technical/soft skills, tools, languages; "
            "experience: jobs, projects, internships; "
            "education: degrees, certifications, courses."
        )
    )

class ResumeFragmentation(BaseModel):
    fragmentation_reasoning: str = Field(
        description=(
            "Explanation of how the resume text was split into fragments (by \\n\\n, \\n, or sentences). "
            "The goal is to capture 100% of the resume text across all sections."
            "Please be brief."
        )
    )
    fragments: Annotated[List[FragmentClassification], MinLen(3)] = Field(description="List of classified fragments, covering the entire resume text")

def extract_fragments(cv_text: str, llm_handler: LLMHandler, model: str) -> ResumeFragmentation:
    """
    Send resume text to LLM, get structured fragmentation and classification.
    Uses dynamic max_tokens: max(len(cv_text) * 5, 1000).
    """
    prompt = [
        {
            "role": "system",
            "content": (
                "You are a resume parsing expert. "
                "1. First, explain how you will split the text into fragments (by \\n\\n, \\n, or sentences). "
                "2. Classify each fragment into one of the sections: header, summary, skills, experience, education. "
                "3. Provide a brief reason (1 sentence) for each classification. "
                "4. Ensure that 100% of the resume text is covered by the fragments. "
                "5. Use only the five specified sections, even if a fragment is ambiguous."
            )
        },
        {
            "role": "user",
            "content": f"Split and classify the following resume text:\n\n{cv_text}"
        }
    ]

    # Dynamic max_tokens calculation
    max_tokens = max(len(cv_text) * 5, 1000)

    # Get structured response from LLM
    response = llm_handler.get_answer(
        prompt,
        model=model,
        response_format=ResumeFragmentation,
        max_tokens=max_tokens
    )

    return response["parsed"]



def find_fragment_position(text: str, fragment: str, threshold: float = 0.75) -> Optional[int]:
    """
    Find the approximate position of a fragment in the text using fuzzy matching.
    Returns the starting index if a match is found, otherwise None.
    """
    if not fragment:
        return None

    fragment_words = fragment.lower().split()
    text_lower = text.lower()
    text_words = text_lower.split()

    best_pos = None
    best_score = 0
    window_size = len(fragment_words)

    for i in range(len(text_words) - window_size + 1):
        window = ' '.join(text_words[i:i + window_size])
        score = SequenceMatcher(None, ' '.join(fragment_words), window).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_pos = text_lower.find(text_words[i])

    return best_pos

def extract_full_sections(cv_text: str, llm_handler: Any, model: str) -> Dict[str, Any]:
    """
    Extracts all sections from the resume using fragment classification.
    Handles gaps and validates coverage.
    """
    start_time = time.time()

    # Step 1: Get fragments from LLM
    fragments_response = llm_handler.get_answer(
        prompt=[
            {
                "role": "system",
                "content": (
                    "You are a resume parsing expert. "
                    "1. First, explain how you will split the text into fragments (by \\n\\n, \\n, or sentences). "
                    "2. Classify each fragment into one of the sections: header, summary, skills, experience, education. "
                    "3. Provide a brief reason (1 sentence) for each classification. "
                    "4. Ensure that 100% of the resume text is covered by the fragments. "
                    "5. Use only the five specified sections, even if a fragment is ambiguous."
                )
            },
            {
                "role": "user",
                "content": f"Split and classify the following resume text:\n\n{cv_text}"
            }
        ],
        model=model,
        max_tokens=max(len(cv_text) * 5, 5000),
        response_format=ResumeFragmentation
    )

    fragments_result = fragments_response['parsed']
    fragments_usage = fragments_response.get('usage', {})
    fragments_cost = fragments_response.get('cost', {})

    # Step 2: Find fragment positions and sort
    fragment_positions = []
    for frag in fragments_result.fragments:
        pos = find_fragment_position(cv_text, frag.fragment)
        if pos is not None:
            fragment_positions.append((pos, frag.fragment, frag.section))

    fragment_positions.sort(key=lambda x: x[0])
    fragment_list = [(frag, section) for pos, frag, section in fragment_positions]

    first_header_pos = next((pos for pos, frag, section in fragment_positions if section == "header"), None)

    # Step 3: Find gaps
    gaps = []
    current_pos = 0
    for pos, frag, section in fragment_positions:
        if pos > current_pos:
            gap_text = cv_text[current_pos:pos].strip()
            if gap_text:
                gaps.append((len(gaps) + 1, gap_text, section))
        current_pos = pos + len(frag)
    if current_pos < len(cv_text):
        gap_text = cv_text[current_pos:].strip()
        if gap_text:
            gaps.append((len(gaps) + 1, gap_text, fragment_list[-1][1] if fragment_list else "unknown"))

    # Step 4: Calculate coverage
    covered_length = sum(len(frag) for frag, _ in fragment_list)
    coverage_percent = (covered_length / len(cv_text)) * 100 if cv_text else 0

    # Step 5: Prepare gaps dictionary
    gaps_dict = {
        f"{i}) {text}": section
        for i, text, section in gaps
    }
    gaps_dict["coverage_percent"] = coverage_percent

    # Step 6: Build sections dictionary
    sections = {}
    for section_name in ["header", "summary", "skills", "experience", "education"]:
        section_fragments = [frag for frag, sec in fragment_list if sec == section_name]
        sections[section_name.capitalize()] = "\n ".join(section_fragments)

    if first_header_pos is not None:
        # Находим все пробелы, которые находятся перед первым фрагментом Header
        header_gaps = [
            gap_text
            for gap_num, gap_text, gap_section in gaps
            if gap_section == "header" and (
                # Проверяем, что позиция пробела меньше позиции первого фрагмента Header
                    cv_text.find(gap_text) < first_header_pos
            )
        ]
        # Добавляем найденные пробелы в начало секции Header
        sections["Header"] = "\n ".join(header_gaps) + "\n " + sections.get("Header", "")

    # Step 7: Validate required sections
    missing_sections = [s for s in MANDATORY_SECTIONS if not sections.get(s)]
    issues = []
    if gaps:
        issues.append(f"Found {len(gaps)} gaps in the resume text.")
    if missing_sections:
        issues.append(f"Missing required sections: {', '.join(missing_sections)}")

    # Step 8: Return result
    return {
        "sections": sections,
        "fragments": fragment_list,
        "Gaps": gaps_dict,
        "issues": issues,
        "validation": {
            "is_valid": not missing_sections,
            "method": "full_fragments_with_gaps",
            "issues": issues,
            "metrics": {
                "sections_found": len(sections),
                "missing_required_sections": missing_sections,
                "coverage_percent": coverage_percent,
            },
            "summary": f"Coverage: {coverage_percent:.1f}%, "
                       f"Missing required sections: {', '.join(missing_sections) if missing_sections else 'None'}"
        },
        "reasoning": fragments_result.fragmentation_reasoning,
        "method": "full_fragments_with_gaps",
        "cost": fragments_cost,
        "token_usage": {
            "prompt_tokens": fragments_usage.prompt_tokens,
            "completion_tokens": fragments_usage.completion_tokens,
        },
        "time": time.time() - start_time
    }

