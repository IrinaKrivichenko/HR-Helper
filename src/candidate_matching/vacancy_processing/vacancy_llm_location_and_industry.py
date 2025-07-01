from src.logger import logger
from src.nlp.llm_handler import LLMHandler


def parse_llm_response(response: str) -> dict:
    # Initialize a dictionary to store extracted data
    extracted_data = {}

    # Split the response into sections
    sections = response.split('- **')

    # Iterate over each section to extract relevant information
    for section in sections:
        if ':' in section:
            # Split section into name and content
            section_name, section_content = section.split('**:', 1)
            section_name = section_name.strip()
            section_content = section_content.strip()

            # Extract industry if present
            if section_name == 'Extracted Industry':
                if not section_content.startswith('No'):
                    # Store industry
                    extracted_data['Extracted Industry'] = section_content

            # Extract location if present
            elif section_name == 'Extracted Location':
                # Store location
                if "remote" in section_content.strip().lower():
                    section_content = "Any location"
                extracted_data['Extracted Location'] = section_content

            # Extract reasoning if present
            elif section_name == 'Reasoning':
                if not section_content.startswith('No'):
                    # Store reasoning
                    extracted_data['Vacancy Reasoning'] = section_content

    return extracted_data

industries_list = [ "Healthcare", "Energy", "Construction", "Fintech",
                   "Real Estate", "Gaming", "Insurance", "E-commerce",
                    "Information Security", "IT", "Retail", "Aviation",
                    "Advertising", "Consultancy", "Telecommunications",
                    "Media", "Ecology", "Education", "Manufacturing",
                    "Food Industry", "Hospitality", "Oil and Gas"
]

def extract_vacancy_location_and_industry(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
    industries = ", ".join(industries_list)

    # Define the prompt for the language model
    prompt = [
        {
            "role": "system",
            "content": "You are an expert in analyzing job descriptions."
        },
        {
            "role": "user",
            "content": (
                "Your task is to process the provided job description and extract the following information:\n\n"
                "1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
                "Explain how you inferred the location and industry.\n"
                "2. Identify the location mentioned in the job description. "
                "Write the location in English and without abbreviations. For example, if 'ЕС' or 'Европа' is mentioned, write 'European Union'. "
                "If multiple countries are mentioned, list them separated by commas, for example, 'Only Poland and Romania' should be written as 'Poland, Romania'. "
                "If countries to exclude are mentioned, prefix them with 'NOT ', for example, 'except Russia and Ukraine' should be written as 'NOT Russia, NOT Ukraine'. "
                "Emojis like ❌ should be interpreted as 'NOT', for example, '❌ RF/RB' should be written as 'NOT Russia, NOT Belarus'. "
                "Note that 'RF' stands for Russia and 'RB' stands for Belarus."
                "If the location is a specific city, write the city name first followed by the country, separated by a comma."
                "Choose the broader geographical coverage if multiple locations are mentioned, for example, if it says 'EU, preferably Poland', then write 'European Union'. "
                "If no location is found or if only the client's location is mentioned without implying the candidate's location, return 'Remote'.\n"
                "If the location is mentioned in the context of the project description without implying the candidate's location, return 'Remote'.\n"
                "3. Identify the industry mentioned in the job description. Select the industry from the following list: "
                f"{industries_list}. "
                "\n"
                "If no industry is found or the industry is not in the list, return 'No industry is found'.\n"
                "The output should be formatted in Markdown with the following sections:\n"
                "- **Reasoning**: The reasoning on how the information was extracted.\n"
                "- **Extracted Location**: The location extracted by the language model from the vacancy description.\n"
                "- **Extracted Industry**: The industry extracted by the language model from the vacancy description.\n"
                "\n"
                "Here are some examples:\n\n"
                "# Example 1:\n"
                "We are seeking an experienced Web Developer to join our dynamic team, supporting the creation and deployment of a cutting-edge website for our expanding network of eateries across 30+ divisions in the EU. Your primary focus will be on designing and implementing a user-friendly and efficient online platform that enhances our production and delivery services. You will work closely with our cross-functional teams to ensure high-quality digital solutions that meet the needs of our diverse customer base. Salary - up to 5000$ gross.\n"
                "\n"
                "- **Reasoning**: The job description specifies that the network operates 'across 30+ divisions in the EU', indicating the client's location within the European Union. However, it does not impose any location requirements on the candidate, leading to the conclusion that the candidate's location is 'Remote'. The industries related to this project are Retail, Logistics, Manufacturing, and E-commerce.\n"
                "- **Extracted Location**: Remote\n"
                "- **Extracted Industry**:\n"
                "  - Retail\n"
                "  - Logistics\n"
                "  - Manufacturing\n"
                "  - E-commerce\n"
                "\n"
                "# Example 2:\n"
                "We are looking for a Senior Front-End Developer to join our team. Candidates must not be located in Russia, Ukraine, or Belarus due to current operational constraints.\n"
                "\n"
                "- **Reasoning**: The job description explicitly excludes candidates located in Russia, Ukraine, or Belarus. This indicates that the candidate's location must not be in these countries, but other locations are acceptable. The job description does not mention any specific industry, so no industry is identified.\n"
                "- **Extracted Location**: NOT Russia, NOT Ukraine, NOT Belarus\n"
                "- **Extracted Industry**: No industry is found\n"
                "\n"
                "# Example 3:\n"
                "Location: Remote (within Europe). We are seeking a skilled Data Analyst to join our retail team. The role involves analyzing data trends and providing insights to support business decisions across our European markets.\n"
                "\n"
                "- **Reasoning**: The job description specifies that the location is 'Remote (within Europe)', indicating that the candidate must be located within Europe but can work remotely from any European country. The mention of joining a 'retail team' suggests the industry is Retail.\n"
                "- **Extracted Location**: European Union\n"
                "- **Extracted Industry**: Retail\n"
                "\n"
                "Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\n"
            )
        }
    ]



    # Calculate max tokens based on the length of the vacancy description
    max_tokens = max(len(vacancy) * 3, 500)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    # Parse the response from the LLM
    extracted_data = parse_llm_response(response)

    return extracted_data



