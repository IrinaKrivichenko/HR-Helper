from pydantic import BaseModel, Field
from typing import Literal

language_codes = {
        "Albanian": "SQ", "Arabic": "AR", "Armenian": "HY", "Azerbaijani": "AZ",
        "Bashkir": "BA", "Belarussian": "BE", "Belarusian": "BE", "Bulgarian": "BG",
        "Chinese": "ZH", "Chuvash": "CV", "Croatian": "HR", "Czech": "CS",
        "Danish": "DA", "Dutch": "NL",
        "English": "EN", "Estonian": "ET",
        "Finnish": "FI", "French": "FR",
        "Georgian": "KA", "German": "DE", "Greek": "EL",
        "Hebrew": "HE", "Hindi": "HI", "Hungarian": "HU",
        "Indonesian": "ID", "Italian": "IT",
        "Japanese": "JA",
        "Kazakh": "KK", "Korean": "KO", "Kyrgyz": "KY",
        "Latvian": "LV", "Lithuanian": "LT",
        "Macedonian": "MK", "Moldovan": "MO", "Mongolian": "MN",
        "Norwegian": "NO",
        "Persian": "FA", "Polish": "PL", "Portuguese": "PT",
        "Romanian": "RO", "Russian": "RU",
        "Serbian": "SR", "Slovak": "SK", "Slovenian": "SL", "Spanish": "ES", "Swedish": "SV",
        "Tajik": "TG", "Tatar": "TT", "Thai": "TH", "Turkish": "TR",
        "Ukrainian": "UK", "Uzbek": "UZ",
        "Vietnamese": "VI",
    }

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
    language: LanguageName = Field(description="Name of the language")
    level: CEFRLevel = Field(description="CEFR level (A1, A2, B1, B2, C1, C2)")
