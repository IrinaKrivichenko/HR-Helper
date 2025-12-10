from typing import Dict

# Field to sections mapping (in priority order)
FIELD_MAPPING = {
    "Name": ["Header"],
    "Email": ["Header"],
    "Phone": ["Header"],
    "Linkedin": ["Header"],
    "Github": ["Header", "Experience"],
    "Telegram": ["Header"],
    "WhatsApp": ["Header"],
    "Location": ["Header"],
    "Stack": ["Skills", "Experience", "Education"],
    "Languages": ["Header", "Skills", "Education"],
    "Expertise": ["Experience", "Education"],
    "Role": ["Header", "Skills", "Experience", "Education"],
    "Seniority": ["Header", "Summary", "Skills", "Experience", "Education"],
    "Industries": ["Summary", "Skills", "Experience", "Education"],
}

def get_section_for_field(cv_sections: Dict[str, str], field_name: str) -> str:
    """
    Get appropriate text for extracting a specific field.
    Args:
        cv_sections: Dictionary of extracted resume sections
        field_name: Name of field to extract (e.g., "Name", "Email", "Stack")
    Returns:
        Text from appropriate section(s) for field extraction
    """
    # Special case for Projects
    if field_name == "Projects":
        if "Projects" in cv_sections:
            return cv_sections["Projects"]
        return []

    # Get text from preferred sections
    preferred_sections = FIELD_MAPPING.get(field_name, [])
    texts = []

    for section_name in preferred_sections:
        # Case-insensitive search
        for key, value in cv_sections.items():
            if key.lower() == section_name.lower() and value:
                texts.append(value)
                break

    # Return combined texts or all sections as fallback
    if texts:
        return "\n\n".join(texts)

    # Fallback: all non-internal sections
    return "\n\n".join(v for k, v in cv_sections.items() if v and not k.startswith("_"))

from typing import Dict, List, Optional

def collect_sections_by_keywords(
    cv_sections: Dict[str, str],
    name_keywords: List[str],                 # передаем [] теперь
    content_keywords: Optional[List[str]] = None,
    case_insensitive: bool = True,
    skip_internal: bool = True
) -> str:
    if not cv_sections:
        return ""

    def norm(s: str) -> str:
        return s.lower() if case_insensitive and isinstance(s, str) else (s or "")

    name_kws = [norm(k) for k in name_keywords if k]
    content_kws = [norm(k) for k in (content_keywords or []) if k]
    parts: List[str] = []
    for sec_name, sec_text in cv_sections.items():
        if not sec_text:
            continue
        if skip_internal and str(sec_name).startswith("_"):
            continue
        nname = norm(str(sec_name))
        ntext = norm(str(sec_text))
        name_hit = any(kw in nname for kw in name_kws) if name_kws else False
        content_hit = any(kw in ntext for kw in content_kws) if content_kws else False
        if name_hit or content_hit:
            parts.append(str(sec_text))
    return "\n".join(dict.fromkeys(parts)).strip()  # легкая дедупликация


