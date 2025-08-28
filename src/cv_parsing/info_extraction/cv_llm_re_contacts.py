import re
import traceback
import phonenumbers
from phonenumbers import geocoder, carrier
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field, validator

from src.nlp.llm_handler import LLMHandler


def normalize_linkedin_url(url: str) -> str:
    """
    Normalize LinkedIn URL to standard format
    """
    if url.startswith(('http://', 'https://')):
        return url
    elif url.startswith('www.linkedin.com'):
        return f"https://{url}"
    elif url.startswith('linkedin.com'):
        return f"https://{url}"
    else:
        # If only username provided
        return f"https://linkedin.com/in/{url}"


def extract_contacts_regex(cv_text: str) -> Tuple[List[str], List[str]]:
    """
    Extract Email and LinkedIn via regex (fast and reliable)
    Returns: (emails, linkedin_urls)
    """

    # Email - very reliable pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, cv_text, re.IGNORECASE)

    # LinkedIn - reliable pattern for all variants
    linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+'
    linkedin_matches = re.findall(linkedin_pattern, cv_text, re.IGNORECASE)

    # Normalize LinkedIn URLs
    linkedin_urls = [normalize_linkedin_url(url) for url in linkedin_matches]

    return emails, linkedin_urls


class PhoneTelegramLocationExtraction(BaseModel):
    reasoning_steps: List[str] = Field(description="Step-by-step analysis for phone, telegram and location extraction")
    phone_numbers: List[str] = Field(default=[], description="Phone numbers found in the resume")
    telegram_handles: List[str] = Field(default=[], description="Telegram usernames or links")
    locations: List[str] = Field(default=[], description="Locations, cities, countries mentioned in resume")
    detected_country: Optional[str] = Field(default=None, description="Primary country detected from resume context")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in extraction")

    @validator('phone_numbers')
    def normalize_phone_numbers(cls, v, values):
        """
        Smart phone normalization using phonenumbers library
        """
        country = values.get('detected_country', '').lower() if values.get('detected_country') else ''
        normalized = []

        # Map country names to ISO codes
        country_mapping = {
            'poland': 'PL', 'polska': 'PL',
            'ukraine': 'UA', 'україна': 'UA',
            'sweden': 'SE', 'sverige': 'SE',
            'cyprus': 'CY', 'κύπρος': 'CY',
            'united states': 'US', 'usa': 'US',
            'united kingdom': 'GB', 'uk': 'GB',
            'germany': 'DE', 'deutschland': 'DE'
        }

        # Determine country code from context
        country_code = None
        for country_name, iso_code in country_mapping.items():
            if country_name in country:
                country_code = iso_code
                break

        for phone in v:
            if phone:
                try:
                    # Try to parse with detected country context
                    if country_code:
                        parsed = phonenumbers.parse(phone, country_code)
                    else:
                        parsed = phonenumbers.parse(phone, None)

                    # Validate and format if valid
                    if phonenumbers.is_valid_number(parsed):
                        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                        normalized.append(formatted)
                    else:
                        # Fallback to basic cleaning
                        clean_phone = re.sub(r'[^\d+]', '', phone)
                        if clean_phone and not clean_phone.startswith('+'):
                            # Basic country code detection
                            if clean_phone.startswith(('48', '380', '46', '357', '1', '44', '49')):
                                clean_phone = f"+{clean_phone}"
                        normalized.append(clean_phone)

                except phonenumbers.NumberParseException:
                    # Fallback to basic cleaning if parsing fails
                    clean_phone = re.sub(r'[^\d+]', '', phone)
                    if clean_phone and not clean_phone.startswith('+'):
                        if clean_phone.startswith(('48', '380', '46', '357', '1', '44', '49')):
                            clean_phone = f"+{clean_phone}"
                    normalized.append(clean_phone)

        return normalized


def extract_phone_telegram_location_sgr(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano") -> Tuple[
    List[str], List[str], List[str], float]:
    """
    Extract Phone, Telegram and Location via SGR (contextual understanding)
    Returns: (phones, telegrams, locations, cost)
    """

    prompt = [
        {
            "role": "system",
            "content": "You are an expert contact and location extractor specializing in resume parsing."
        },
        {
            "role": "user",
            "content": (
                f"Extract phone numbers, Telegram contacts, and location information from this resume.\n\n"
                f"**Phone Rules:**\n"
                f"1. Find all phone numbers (mobile, work, any format)\n"
                f"2. Ignore fax numbers, extension numbers, postal codes, years\n"
                f"3. Include country codes when possible\n"
                f"4. Examples: '+380639941464', '(46) 76-500-5316', '+48 728291199'\n\n"
                f"**Telegram Rules:**\n"
                f"1. Find Telegram usernames (@username)\n"
                f"2. Find Telegram links (t.me/username, telegram.me/username)\n"
                f"3. Distinguish from Twitter @mentions using context\n"
                f"4. Look for 'Telegram:', 'TG:', or similar indicators\n\n"
                f"**Location Rules:**\n"
                f"1. Find cities, countries, regions mentioned in resume\n"
                f"2. Include current location, work locations, addresses\n"
                f"3. Examples: 'Stockholm, Sweden', 'Poland', 'Limassol, Cyprus'\n"
                f"4. Ignore company names that sound like locations\n\n"
                f"**Country Detection:**\n"
                f"1. Identify the primary country/location mentioned in resume\n"
                f"2. Use this context for phone number normalization\n"
                f"3. Look for city names, addresses, country indicators\n\n"
                f"**Resume:**\n{cv}"
            )
        }
    ]

    try:
        response = llm_handler.get_answer(
            prompt, model=model, max_tokens=400,
            response_format=PhoneTelegramLocationExtraction
        )

        extraction = response['parsed']
        cost = response['cost']['total_cost']

        return extraction.phone_numbers, extraction.telegram_handles, extraction.locations, cost

    except Exception as e:
        print(f"SGR extraction failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return [], [], [], 0.0


def extract_contacts(cv: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    """
    Hybrid contact extraction: regex for Email/LinkedIn, SGR for Phone/Telegram/Location
    """

    # Fast extraction via regex
    emails, linkedin_urls = extract_contacts_regex(cv)

    # Contextual extraction via SGR
    phones, telegrams, locations, sgr_cost = extract_phone_telegram_location_sgr(cv, llm_handler, model)

    # Build result dictionary
    result = {
        "Email": ', '.join(emails) if emails else "",
        "LinkedIn": ', '.join(linkedin_urls) if linkedin_urls else "",
        "Phone": ', '.join(phones) if phones else "",
        "Telegram": ', '.join(telegrams) if telegrams else "",
        "Location": ', '.join(locations) if locations else ""
    }

    if add_tokens_info:
        result["Reasoning about Contacts"] = f"Email/LinkedIn extracted via regex, Phone/Telegram/Location via SGR"
        result["Model Used"] = model
        result["SGR Cost"] = f"${sgr_cost:.6f}"
        result["Regex Items"] = f"Emails: {len(emails)}, LinkedIn: {len(linkedin_urls)}"
        result["SGR Items"] = f"Phones: {len(phones)}, Telegrams: {len(telegrams)}, Locations: {len(locations)}"
    else:
        result["Cost_of_Contacts_CV_extraction"] = sgr_cost

    return result
