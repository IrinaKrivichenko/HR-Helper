from typing import Dict, Optional, List
import random
from datetime import datetime
import time
import json
import traceback
from typing import List, Optional, Annotated

from annotated_types import MaxLen
from pydantic import BaseModel, Field, validator

from src.data_processing.nlp.countries_info import get_random_vacancy_locations, \
    COUNTRIES_NAMES_WITH_NOT, COUNTRIES_NAMES
from src.data_processing.nlp.llm_handler import LLMHandler
from src.logger import logger



class VacancyLocationExtraction(BaseModel):
    reasoning_about_eu: Annotated[List[str], MaxLen(3)] = Field(description="Reasoning about whether the European Union is explicitly mentioned. Provide no more than a couple of sentences.")
    eu_term: Optional[str] = Field(default=None, description="The exact word or phrase used to refer to the EU in the vacancy text.")
    european_union: bool = Field(description="Boolean indicating if the European Union is explicitly mentioned. Must be True only if `eu_term` is found in the vacancy text.")
    reasoning_about_timezone: Annotated[List[str], MaxLen(6)] = Field(description="Reasoning about time zone requirements. Provide no more than a couple of sentences.")
    timezone_countries: List[COUNTRIES_NAMES] = Field(default=[], description="List of countries from the specified time zone. If no time zone is mentioned, leave the list empty.")
    reasoning_about_preferred: Annotated[List[str], MaxLen(3)] = Field(description="Reasoning about explicitly mentioned preferred countries. Provide no more than a couple of sentences.")
    preferred_countries: List[COUNTRIES_NAMES] = Field(default=[],description="List of explicitly mentioned preferred countries.")
    reasoning_about_excluded: Annotated[List[str], MaxLen(3)] = Field(description="Reasoning about countries that need to be excluded. Provide no more than a couple of sentences.")
    excluded_countries: List[COUNTRIES_NAMES_WITH_NOT] = Field(default=[], description="List of countries with NOT prefix.")
    reasoning_about_remote: Annotated[List[str], MaxLen(3)] = Field(description="Reasoning about whether remote work is possible. Provide no more than a couple of sentences.")
    remote: bool = Field(description="Boolean indicating if remote work is possible.")
    reasoning_about_cities: Annotated[List[str], MaxLen(3)] = Field(description="Reasoning about explicitly mentioned cities. Provide no more than a couple of sentences.")
    cities: List[str] = Field(default=[], description="List of cities if mentioned in the vacancy.")

    @validator("european_union")
    def validate_eu_mention(cls, v, values):
        if v and not values.get("eu_term"):
            raise ValueError("If european_union is True, eu_term must be provided.")
        return v

def parse_locations(extraction: VacancyLocationExtraction, vacancy_text: str):
    # Combine preferred_countries and timezone_countries using a set to avoid duplicates
    preferred_locations = set(extraction.preferred_countries) | set(extraction.timezone_countries)
    # Convert back to a sorted list
    preferred_locations_list = sorted(preferred_locations)
    # Prepare the "Extracted Location" list
    extracted_location = []
    # Add excluded countries (sorted alphabetically)
    if extraction.excluded_countries:
        extracted_location.extend(sorted(extraction.excluded_countries))
    # Add "Remote" if remote is True
    if extraction.remote:
        extracted_location.append("Remote")
    # Add "European Union" if european_union is True
    if extraction.european_union:
        if extraction.eu_term in vacancy_text.lower() or extraction.eu_term.lower() in vacancy_text.lower():
            extracted_location.append("European Union")
    # Add the combined list of preferred countries and timezone countries (sorted alphabetically)
    if preferred_locations_list and len(preferred_locations_list)<15:
        extracted_location.extend(preferred_locations_list)
    # Add cities if specified (sorted alphabetically)
    if extraction.cities:
        extracted_location.extend(sorted(extraction.cities))
    return extracted_location


def extract_vacancy_location(
    vacancy: str,
    llm_handler: 'LLMHandler',
    model: str = "gpt-4.1-mini",
    add_tokens_info: bool = False
) -> Dict[str, str]:
    """
    Extracts location information from a vacancy using LLM.

    Args:
        vacancy (str): The vacancy text.
        llm_handler (LLMHandler): Handler for LLM interactions.
        model (str): Model to use for extraction.
        add_tokens_info (bool): If True, adds token usage information to the result.

    Returns:
        Dict[str, str]: Dictionary with extracted location information.
    """

    # Form the prompt
    # Generate random countries for the example
    eu_countries = get_random_vacancy_locations(count=2, eu_filter="eu_only", with_flag=False)
    non_eu_countries = get_random_vacancy_locations(count=2, eu_filter="non_eu_only", with_flag=False)
    emoji_example = random.choice(["❌", "🚫", "🙅", "⛔", "💢"])
    "8. **Example**: If the location is stated as "
    f"'EU preferred, {eu_countries[0]} or {eu_countries[1]}, {emoji_example}{non_eu_countries[0]}/{non_eu_countries[1]}, but remote work is also possible.', "
    f"the result should be 'European Union, {eu_countries[0]}, {eu_countries[1]}, NOT {non_eu_countries[0]}, NOT {non_eu_countries[1]}, Remote'.\n"

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an expert in extracting location information from job vacancies. "
                "Follow these rules strictly to fill in the fields of the VacancyLocationExtraction model:\n\n"
                "1. **reasoning_about_eu**:\n"
                "   - Provide reasoning about whether the European Union is explicitly mentioned.\n"
                "   - Examples of EU mentions include: 'Europe', 'EU', 'European Union', 'ЕС', 'Євросоюз' etc.\n"
                "2. **eu_term**:\n"
                "   - The exact word or phrase used to refer to the European Union in the vacancy text.\n"
                "   - If the EU is mentioned, this field must contain the exact term used.\n"
                "3. **european_union**:\n"
                "   - Boolean indicating if the European Union is explicitly mentioned.\n"
                "   - Must be True only if `eu_term` is found in the vacancy text.\n"
                "4. **reasoning_about_timezone**:\n"
                "   - Provide reasoning about time zone requirements.\n"
                "   - If the vacancy explicitly mentions a time zone ('CET', 'UTC', 'GMT'), list ONLY the countries that strictly match this time zone or range.\n"
                "   - If no time zone is mentioned, leave this field empty.\n"
                "5. **timezone_countries**:\n"
                "   - List of countries from the specified time zone.\n"
                "   - If no time zone is mentioned, leave the list empty.\n"
                "6. **reasoning_about_preferred**:\n"
                "   - Provide reasoning about explicitly mentioned preferred countries.\n"
                "   - Including those countries that were defined using time zones.\n"
                f"  - Example: If the location in the vacancy is described like 'EU, but preferred {eu_countries[0]} or {eu_countries[1]}', the result should be '{eu_countries[0]}, {eu_countries[1]}'.\n"
                "7. **preferred_countries**:\n"
                "    - List explicitly mentioned preferred countries.\n"
                "8. **reasoning_about_excluded**:\n"
                "   - Provide reasoning about countries that need to be excluded.\n"
                "   - Only include countries in the excluded list if they are explicitly mentioned as excluded.\n"
                "   - An indication of a specific location does not imply that all other locations should be excluded unless explicitly stated.\n"
                "   - Look for phrases like 'not', 'except', 'excluding', or emojis like ❌, 🚫, 🙅, ⛔, 💢.\n"
                "   - If there are no explicit mentions of excluded countries, leave this field empty.\n"
                f"  - Example: If the location in the vacancy is described like '{emoji_example}{non_eu_countries[0]}/{non_eu_countries[1]}', the result of excluded_countries should be 'NOT {non_eu_countries[0]}, NOT {non_eu_countries[1]}'.\n"
                "9. **excluded_countries**:\n"
                "   - List countries that need to be excluded, prefixed with 'NOT '.\n"
                "10. **reasoning_about_remote**:\n"
                "   - Provide reasoning about whether remote work is possible.\n"
                "   - If no location is found or if only the client's location is mentioned without implying the candidate's location, set 'remote' to true.\n"
                "   - If the nature of the project suggests flexibility in terms of location, set 'remote' to true.\n"
                "   - If the location is mentioned in the context of the project description without implying the candidate's location, set 'remote' to true.\n"
                "11. **remote**:\n"
                "    - Boolean indicating if remote work is possible.\n"
                "    - Set to true if the vacancy suggests flexibility in terms of location.\n"
                "12. **reasoning_about_cities**:\n"
                "    - Provide reasoning about explicitly mentioned cities.\n"
                "13. **cities**:\n"
                "    - If specific cities are mentioned, list them.\n"

            )
        },
        {
            "role": "user",
            "content": (
                f"Extract the location information from this vacancy. Follow the rules above strictly.\n"
                f"Return the result in JSON format with the fields of the VacancyLocationExtraction model.\n\n"
                f"**Vacancy:**\n{vacancy}"
            )
        }
    ]


    start_time = time.time()
    response = llm_handler.get_answer(
        prompt,
        model=model,
        max_tokens=2000,
        response_format=VacancyLocationExtraction
    )

    extraction = response['parsed']
    usage = response['usage']
    cost_info = response['cost']

    # Prepare the "Extracted Location" list
    extracted_location = parse_locations(extraction, vacancy)

    # Prepare the "Vacancy Location Reasoning" text
    reasoning_text = (
        f"Reasoning about European Union:\n{' '.join(extraction.reasoning_about_eu)}\n"
        f"Term used for EU: {extraction.eu_term if extraction.eu_term else 'Not mentioned'}\n"
        f"European Union mentioned: {extraction.european_union}\n\n"

        f"Reasoning about timezone:\n{' '.join(extraction.reasoning_about_timezone)}\n"
        f"Countries from specified timezone: {', '.join(extraction.timezone_countries) if extraction.timezone_countries else 'None'}\n\n"

        f"Reasoning about preferred countries:\n{' '.join(extraction.reasoning_about_preferred)}\n"
        f"Preferred countries: {', '.join(extraction.preferred_countries) if extraction.preferred_countries else 'None'}\n\n"

        f"Reasoning about excluded countries:\n{' '.join(extraction.reasoning_about_excluded)}\n"
        f"Excluded countries: {', '.join(extraction.excluded_countries) if extraction.excluded_countries else 'None'}\n\n"

        f"Reasoning about remote work:\n{' '.join(extraction.reasoning_about_remote)}\n"
        f"Remote work possible: {extraction.remote}\n\n"

        f"Reasoning about cities:\n{' '.join(extraction.reasoning_about_cities) if hasattr(extraction, 'reasoning_about_cities') and extraction.reasoning_about_cities else 'None'}\n"
        f"Cities: {', '.join(extraction.cities) if extraction.cities else 'Not mentioned'}\n"
    )

    if add_tokens_info:
        result = {
            "Extracted Location": extracted_location,
            "Vacancy Location Reasoning": reasoning_text,
            "Model Used vacancy_location": model,
            "Completion Tokens vacancy_location": str(usage.completion_tokens),
            "Prompt Tokens vacancy_location": str(usage.prompt_tokens),
            "Cost vacancy_location": str(cost_info['total_cost'])
        }
    else:
        result = {
            "Extracted Location": extracted_location,
            "Vacancy Location Reasoning": reasoning_text,
            "Model Used vacancy_location": model,
            "Cost vacancy_location": str(cost_info['total_cost'])
        }

    result["Time"] = str(time.time() - start_time)

    logger.info(
        f"Vacancy location extraction completed | Response: {json.dumps(result, ensure_ascii=False)}"
    )

    return result

#
# def parse_llm_vacancy_location_response(response: str, add_tokens_info: bool) -> dict:
#     # Initialize a dictionary to store extracted data
#     extracted_data = {}
#
#     # Split the response into sections
#     sections = response.split('##')
#
#     # Iterate over each section to extract relevant information
#     for section in sections:
#         if ':' in section:
#             # Split section into name and content
#             section_name, section_content = section.split(':', 1)
#             section_name = section_name.strip()
#             section_content = section_content.strip()
#
#             # Extract location if present
#             if section_name == "Candidate's Location":
#                 # Store location
#                 if "remote" in section_content.strip().lower():
#                     section_content = "Any location"
#                 extracted_data['Extracted Location'] = section_content
#
#             # Extract reasoning if present
#             elif section_name == 'Reasoning':
#                 if not section_content.startswith('No'):
#                     # Store reasoning
#                     extracted_data['Vacancy Location Reasoning'] = section_content
#
#             # Parse token usage and cost information
#             elif section_name == 'Token Usage and Cost':
#                 print("add_tokens_info", add_tokens_info)
#                 token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_location", add_tokens_info=add_tokens_info)
#                 extracted_data.update(token_data)
#
#     return extracted_data
#
#
# def extract_vacancy_location(vacancy: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
#
#     # Define the prompt for the language model
#     prompt = [
#         {
#             "role": "system",
#             "content": "You are an expert in analyzing job descriptions."
#         },
#         {
#             "role": "user",
#             "content": (
#                 "Your task is to process the provided job description and extract the following information:\n\n"
#                 "1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
#                 "Explain how you inferred the preferred candidate's location.\n"
#                 "2. Identify the candidate's location mentioned in the job description. "
#                 "Write the location in English and without abbreviations. For example, if 'ЕС' or 'Европа' is mentioned, write 'European Union'. "
#                 "If multiple countries are mentioned, list them separated by commas, for example, 'Only Poland and Romania' should be written as 'Poland, Romania'. "
#                 "If countries to exclude are mentioned, prefix them with 'NOT ', for example, 'except Russia and Ukraine' should be written as 'NOT Russia, NOT Ukraine'. "
#                 "Emojis like ❌ should be interpreted as 'NOT', for example, '❌ RF/RB' should be written as 'NOT Russia, NOT Belarus'. "
#                 "Note that 'RF' stands for Russia and 'RB' stands for Belarus."
#                 "If the location is a specific city, write the city name first followed by the country, separated by a comma."
#                 "Choose the broader geographical coverage if multiple locations are mentioned, for example, if it says 'EU, preferably Poland', then write 'European Union'. "
#                 "If no location is found or if only the client's location is mentioned without implying the candidate's location, return 'Remote'.\n"
#                 "If the location is mentioned in the context of the project description without implying the candidate's location, return 'Remote'.\n"
#                 "\n"
#                 "The output should be formatted in Markdown with the following sections:\n"
#                 "## Reasoning: The reasoning on how the information was extracted.\n"
#                 "## Candidate's Location: The location extracted by the language model from the vacancy description.\n"
#                 "\n"
#                 "Here are some examples:\n\n"
#                 "# Example 1 Input:\n"
#                 "We are seeking an experienced Web Developer to join our dynamic team, supporting the creation and deployment of a cutting-edge website for our expanding major banking group across 30+ subsidiaries in the EU. Your primary focus will be on designing and implementing a user-friendly and efficient online platform. You will work closely with our cross-functional teams to ensure high-quality digital solutions that meet the needs of our diverse customer base. Salary - up to 5000$ gross.\n"
#                 "\n"
#                 "## Reasoning: The job description specifies that the project supports a major banking group across '30+ subsidiaries in the EU,' indicating that the client operates within the European Union. However, the description emphasizes collaboration with technical teams and data management, which are activities that can be performed remotely. There is no explicit mention of a required candidate location, nor are there any restrictions or preferences for specific countries. The absence of location constraints and the nature of the tasks suggest that the candidate can work remotely, regardless of their specific location within or outside the EU.\n"
#                 "## Candidate's Location: Remote\n"
#                 "\n"
#                 "# Example 2 Input:\n"
#                 "We are looking for a Senior Front-End Developer to join our team. Any location – Open to all countries RU, UA, or BY due to current operational constraints.\n"
#                 "\n"
#                 "## Reasoning: The job description explicitly states 'Any location – Open to all countries except RU, UA, or BY,' indicating that candidates from all countries are eligible except those from Russia, Ukraine, and Belarus. The phrase 'Any location' typically suggests a remote or globally accessible position. However, the explicit exclusion of Russia, Ukraine, and Belarus means that while the position is open to candidates from any other country, it is not available to those based in these excluded countries. Therefore, the location should be summarized with the specific exclusions mentioned."
#                 "## Candidate's Location: NOT Russia, NOT Ukraine, NOT Belarus\n"
#                 "\n"
#                 "# Example 3 Input:\n"
#                 "Location: Remote (within Europe). We are seeking a skilled Data Analyst to join our retail team. The role involves analyzing data trends and providing insights to support business decisions across our European markets.\n"
#                 "\n"
#                 "## Reasoning: The job description specifies that the location is 'Remote (within Europe)', indicating that the candidate must be located within Europe but can work remotely from any European country.\n"
#                 "## Candidate's Location: European Union\n"
#                 "\n"
#                 "# Example 4 Input:\n"
#                 "Tech: Node + React + TypeScript on AWS with PostgreSQL core  \nEnglish: B2  \nExperience: Senior  \nLocation: Any except Cyprus and Israel   \nProject: All in one cloud-based platform that enables businesses to manage operations  \n"
#                 "\n"
#                 "## Reasoning: The job description explicitly states \"Location: Any except Cyprus and Israel,\" which indicates that candidates should not be located in these countries, Since no other specific location is mentioned, and the project involves developing a smartwatch app with no geographical restrictions specified for the candidate, the safest inference is that the position is open to candidates outside Cyprus and Israel, potentially globally, The mention of \"Детали в лс\" (details in private message) suggests that further specifics might be provided privately, but based solely on the provided text, the location restriction is clear, Therefore, the extracted location is \"NOT Cyprus, NOT Israel,\"\n"
#                 "## Candidate's Location: NOT Cyprus, NOT Israel\n"
#                 "\n"
#                 "# Example 5 Input:\n"
#                 "Senior/Lead Flutter Developer (Frontend)  \nПроект: messaging platform  \nДлительность: 3+ months, fulltime  \nКлиент: EU  \nAнглийский: В2 и выше  \nЛокация: EU (желательно Польша, Варшава)  \n"
#                 "\n"
#                 "## Reasoning: The job description explicitly mentions the location as \"EU (желательно Польша, Варшава)\", which indicates that the preferred location is Poland, specifically Warsaw, within the European Union, Since the description states \"желательно\" (preferably), it suggests that the candidate should ideally be located in Warsaw, Poland, but the broader location is the European Union, The mention of \"EU\" as the project client also supports the broader geographical scope, No other locations are specified or implied, and the role appears to be open to candidates within the EU, with a preference for Poland, Warsaw,\n"
#                 "## Candidate's Location: European Union, Poland, Warsaw\n"
#                 "\n"
#                 "# Example 6 Input:\n"
#                 "🔎Full-Stack Engineers \nStack: Go, ,NET, Node, TS, React, AWS \nNot looking for any specific language, but .NET and Golang developers tend to do best\nProject: Fintech/consumer app/crypto  \nVery interesting domain, including agentic AI, crypto, and a self-service B2B2C SaaS product\nDuration: 3+ months with extension for the best candidates out of the team of 12 people\nEngagement: Full-time\nRequirements: Math, algorithms, strong tech background, Polish and English are must-have,  \nLooking for solid experience with web technologies, backend, and any statically typed or functional language (Java, ,NET, Kotlin, Scala, Clojure, etc,)\n"
#                 "\n"
#                 "## Reasoning: The job description specifies that the candidate must speak Polish and English, which might suggest a connection to Poland or Polish-speaking markets. However, language requirements do not necessarily dictate the physical location of the role. The job description does not explicitly mention a specific city or geographical area, nor does it restrict the candidate's location to Poland. There is also no explicit mention of the need for the candidate to be on-site. Given the context and the nature of roles in the fintech/crypto industries, which often support remote work arrangements, the most logical inference is that the position can be performed remotely. The industries is clearly fintech/crypto, as indicated by the project description mentioning 'Fintech/consumer app/crypto' and related technologies like agentic AI and SaaS products, which are conducive to remote work environments.\n"
#                 "## Candidate's Location: Remote\n"
#                 "\n"
#                 "# Example 7 Input:\n"
#                 "We are looking for a Backend Developer with expertise in Java and Spring Boot. The role involves developing and maintaining robust server-side applications. Location: except for Portugal (preferably not in Spain and Italy yet, but such options can be considered).\n"
#                 "\n"
#                 "## Reasoning: The job description specifies that the location should be \"except for Portugal,\" indicating that candidates from Portugal are not being considered for this role. While it mentions a preference against candidates from Spain and Italy, it also states that such options can still be considered. Therefore, the primary restriction is on candidates located in Portugal. The description does not impose strict restrictions on Spain and Italy, implying flexibility. Thus, the location should be summarized with the specific exclusion mentioned.\n"
#                 "## Candidate's Location: NOT Portugal\n"
#                 "\n"
#                 "Here is the input:\n\n"
#                 f"# Job Description:\n"
#                 f"{vacancy}\n"
#             )
#         }
#     ]
#
#
#
#     # Calculate max tokens based on the length of the vacancy description
#     max_tokens = max(len(vacancy) * 3, 500)
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#
#     print(response)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_vacancy_location_response(response, add_tokens_info=add_tokens_info)
#
#     return extracted_data
