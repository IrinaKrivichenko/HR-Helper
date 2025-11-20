from typing import Dict

# Field to sections mapping (in priority order)
FIELD_MAPPING = {
    "Name": ["Header"],
    "Email": ["Header"],
    "Phone": ["Header"],
    "Linkedin": ["Header"],
    "Github": ["Header"],
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
