from pydantic import BaseModel, Field
from typing import Literal

# Список поддерживаемых языков
LanguageName = Literal[
    "Albanian", "Arabic", "Armenian", "Azerbaijani",
    "Bashkir", "Belarussian", "Belarusian", "Bulgarian",
    "Chinese", "Chuvash", "Croatian", "Czech",
    "Danish", "Dutch",
    "English", "Estonian",
    "Finnish", "French",
    "Georgian", "German", "Greek",
    "Hebrew", "Hindi", "Hungarian",
    "Indonesian", "Italian",
    "Japanese",
    "Kazakh", "Korean", "Kyrgyz",
    "Latvian", "Lithuanian",
    "Macedonian", "Moldovan", "Mongolian",
    "Norwegian",
    "Persian", "Polish", "Portuguese",
    "Romanian", "Russian",
    "Serbian", "Slovak", "Slovenian", "Spanish", "Swedish",
    "Tajik", "Tatar", "Thai", "Turkish",
    "Ukrainian", "Uzbek",
    "Vietnamese"
]

CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

class LanguageItem(BaseModel):
    """Structured representation of a language and its CEFR proficiency level."""
    language: LanguageName = Field(description="Name of the language (from the supported list)")
    level: CEFRLevel = Field(description="CEFR level (A1, A2, B1, B2, C1, C2)")
