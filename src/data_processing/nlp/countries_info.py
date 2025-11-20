import random
from typing import Literal, get_args, List

# List of EU countries (without flags)
EU_COUNTRIES = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus",
    "Czech Republic", "Denmark", "Estonia", "Finland", "France",
    "Germany", "Greece", "Hungary", "Ireland", "Italy",
    "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden"
]

COUNTRIES_DATA = {
    "Andorra": "🇦🇩",
    "United Arab Emirates": "🇦🇪",
    "Afghanistan": "🇦🇫",
    "Antigua and Barbuda": "🇦🇬",
    "Albania": "🇦🇱",
    "Armenia": "🇦🇲",
    "Angola": "🇦🇴",
    "Argentina": "🇦🇷",
    "Austria": "🇦🇹",
    "Australia": "🇦🇺",
    "Azerbaijan": "🇦🇿",
    "Bosnia and Herzegovina": "🇧🇦",
    "Barbados": "🇧🇧",
    "Bangladesh": "🇧🇩",
    "Belgium": "🇧🇪",
    "Burkina Faso": "🇧🇫",
    "Bulgaria": "🇧🇬",
    "Bahrain": "🇧🇭",
    "Burundi": "🇧🇮",
    "Benin": "🇧🇯",
    "Brunei": "🇧🇳",
    "Bolivia": "🇧🇴",
    "Brazil": "🇧🇷",
    "Bahamas": "🇧🇸",
    "Bhutan": "🇧🇹",
    "Botswana": "🇧🇼",
    "Belarus": "🇧🇾",
    "Belize": "🇧🇿",
    "Canada": "🇨🇦",
    "Democratic Republic of the Congo": "🇨🇩",
    "Central African Republic": "🇨🇫",
    "Republic of the Congo": "🇨🇬",
    "Switzerland": "🇨🇭",
    "Côte d'Ivoire": "🇨🇮",
    "Cook Islands": "🇨🇰",
    "Chile": "🇨🇱",
    "Cameroon": "🇨🇲",
    "China": "🇨🇳",
    "Colombia": "🇨🇴",
    "Costa Rica": "🇨🇷",
    "Cuba": "🇨🇺",
    "Cape Verde": "🇨🇻",
    "Cyprus": "🇨🇾",
    "Czech Republic": "🇨🇿",
    "Germany": "🇩🇪",
    "Djibouti": "🇩🇯",
    "Denmark": "🇩🇰",
    "Dominican Republic": "🇩🇴",
    "Algeria": "🇩🇿",
    "Ecuador": "🇪🇨",
    "Estonia": "🇪🇪",
    "Egypt": "🇪🇬",
    "Eritrea": "🇪🇷",
    "Spain": "🇪🇸",
    "Ethiopia": "🇪🇹",
    "Finland": "🇫🇮",
    "Fiji": "🇫🇯",
    "Micronesia": "🇫🇲",
    "France": "🇫🇷",
    "Gabon": "🇬🇦",
    "United Kingdom": "🇬🇧",
    "Grenada": "🇬🇩",
    "Georgia": "🇬🇪",
    "Ghana": "🇬🇭",
    "Greece": "🇬🇷",
    "Guatemala": "🇬🇹",
    "Guinea": "🇬🇳",
    "Guinea-Bissau": "🇬🇼",
    "Guyana": "🇬🇾",
    "Honduras": "🇭🇳",
    "Croatia": "🇭🇷",
    "Haiti": "🇭🇹",
    "Hungary": "🇭🇺",
    "Indonesia": "🇮🇩",
    "Ireland": "🇮🇪",
    "Israel": "🇮🇱",
    "India": "🇮🇳",
    "Iraq": "🇮🇶",
    "Iran": "🇮🇷",
    "Iceland": "🇮🇸",
    "Italy": "🇮🇹",
    "Jamaica": "🇯🇲",
    "Jordan": "🇯🇴",
    "Japan": "🇯🇵",
    "Kenya": "🇰🇪",
    "Kyrgyzstan": "🇰🇬",
    "Cambodia": "🇰🇭",
    "Kiribati": "🇰🇮",
    "Comoros": "🇰🇲",
    "Saint Kitts and Nevis": "🇰🇳",
    "North Korea": "🇰🇵",
    "South Korea": "🇰🇷",
    "Kuwait": "🇰🇼",
    "Kazakhstan": "🇰🇿",
    "Laos": "🇱🇦",
    "Lebanon": "🇱🇧",
    "Saint Lucia": "🇱🇨",
    "Liechtenstein": "🇱🇮",
    "Sri Lanka": "🇱🇰",
    "Liberia": "🇱🇷",
    "Lesotho": "🇱🇸",
    "Lithuania": "🇱🇹",
    "Luxembourg": "🇱🇺",
    "Latvia": "🇱🇻",
    "Libya": "🇱🇾",
    "Morocco": "🇲🇦",
    "Monaco": "🇲🇨",
    "Moldova": "🇲🇩",
    "Montenegro": "🇲🇪",
    "Madagascar": "🇲🇬",
    "Marshall Islands": "🇲🇭",
    "North Macedonia": "🇲🇰",
    "Mali": "🇲🇱",
    "Myanmar": "🇲🇲",
    "Mongolia": "🇲🇳",
    "Mozambique": "🇲🇿",
    "Mexico": "🇲🇽",
    "Malta": "🇲🇹",
    "Namibia": "🇳🇦",
    "Niger": "🇳🇪",
    "Nigeria": "🇳🇬",
    "Nicaragua": "🇳🇮",
    "Netherlands": "🇳🇱",
    "Norway": "🇳🇴",
    "Nepal": "🇳🇵",
    "New Zealand": "🇳🇿",
    "Oman": "🇴🇲",
    "Panama": "🇵🇦",
    "Peru": "🇵🇪",
    "Philippines": "🇵🇭",
    "Pakistan": "🇵🇰",
    "Poland": "🇵🇱",
    "Portugal": "🇵🇹",
    "Palau": "🇵🇼",
    "Paraguay": "🇵🇾",
    "Qatar": "🇶🇦",
    "Romania": "🇷🇴",
    "Serbia": "🇷🇸",
    "Russia": "🇷🇺",
    "Rwanda": "🇷🇼",
    "Saudi Arabia": "🇸🇦",
    "Solomon Islands": "🇸🇧",
    "Seychelles": "🇸🇨",
    "Sudan": "🇸🇩",
    "Sweden": "🇸🇪",
    "Singapore": "🇸🇬",
    "Slovenia": "🇸🇮",
    "Slovakia": "🇸🇰",
    "Sierra Leone": "🇸🇱",
    "San Marino": "🇸🇲",
    "Senegal": "🇸🇳",
    "Somalia": "🇸🇴",
    "Suriname": "🇸🇷",
    "South Sudan": "🇸🇸",
    "São Tomé and Príncipe": "🇸🇹",
    "El Salvador": "🇸🇻",
    "Syria": "🇸🇾",
    "Eswatini": "🇸🇿",
    "Tajikistan": "🇹🇯",
    "Thailand": "🇹🇭",
    "Togo": "🇹🇬",
    "Tunisia": "🇹🇳",
    "Turkmenistan": "🇹🇲",
    "East Timor": "🇹🇱",
    "Turkey": "🇹🇷",
    "Trinidad and Tobago": "🇹🇹",
    "Tuvalu": "🇹🇻",
    "Ukraine": "🇺🇦",
    "Uganda": "🇺🇬",
    "United States": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
    "Vatican City": "🇻🇦",
    "Saint Vincent and the Grenadines": "🇻🇨",
    "Venezuela": "🇻🇪",
    "Vietnam": "🇻🇳",
    "Vanuatu": "🇻🇺",
    "Samoa": "🇼🇸",
    "Yemen": "🇾🇪",
    "South Africa": "🇿🇦",
    "Zambia": "🇿🇲",
    "Zimbabwe": "🇿🇼",
}


CountryFlag = Literal[
    *[
        f"{flag}{country}"
        for country, flag in COUNTRIES_DATA.items()
    ],
    "❓UNKNOWN COUNTRY",
    "NO COUNTRY FOUND"
]

country_names_list = list(COUNTRIES_DATA.keys())
COUNTRIES_NAMES = Literal[*country_names_list]

country_names_with_not_list = [f"NOT {country}" for country in country_names_list]
COUNTRIES_NAMES_WITH_NOT = Literal[*country_names_with_not_list]


EUFilter = Literal["eu_only", "non_eu_only", "any"]

def get_random_vacancy_locations(
    count: int,
    with_flag: bool = False,
    eu_filter: EUFilter = "any"
) -> List[str]:
    """
    Returns a list of random vacancy locations based on the specified parameters.
    Args:
        count (int): Number of locations to return.
        with_flag (bool): If True, returns locations with emoji flags.
        eu_filter (EUFilter): Filter by EU membership:
            - "eu_only" — only EU countries.
            - "non_eu_only" — only non-EU countries.
            - "any" — all countries (default).
    Returns:
        List[str]: List of random vacancy locations matching the criteria.
    """
    if eu_filter == "eu_only":
        countries = EU_COUNTRIES.copy()
    elif eu_filter == "non_eu_only":
        countries = [country for country in COUNTRIES_DATA.keys() if country not in EU_COUNTRIES]
    else:  # "any"
        countries = COUNTRIES_DATA.keys()
    # Select random locations
    selected_countries = random.sample(countries, min(count, len(countries)))
    if with_flag:
        selected_countries = [
            f"{COUNTRIES_DATA.get(location.replace('NOT ', ''), '')}{location}"
            if location.replace('NOT ', '') in COUNTRIES_DATA
            else location
            for location in selected_countries
        ]
    return selected_countries



if __name__ == "__main__":
    countries_list = get_args(CountryFlag)
    print(len(countries_list))
    countries_list = get_args(VacancyLocation)
    print(len(countries_list))



