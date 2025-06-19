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

            # Extract technologies if present
            if section_name == 'Extracted Programming Languages':
                if not section_content.startswith('No'):
                    # Clean and store programming languages
                    languages = [lang.strip('- ').strip() for lang in section_content.split('\n') if lang.strip()]
                    extracted_data['Extracted Programming Languages'] = '\n'.join(languages)
            elif section_name == 'Extracted Technologies':
                if not section_content.startswith('No'):
                    # Clean and store technologies
                    technologies = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
                    extracted_data['Extracted Technologies'] = '\n'.join(technologies)
            elif section_name == 'Extracted Role':
                if not section_content.startswith('No'):
                    # Store role
                    roles = [role.strip('- ').strip() for role in section_content.split('\n') if role.strip()]
                    extracted_data['Extracted Role'] = '\n'.join(roles)
            elif section_name == 'Extracted Seniority':
                if not section_content.startswith('No'):
                    # Store seniority
                    extracted_data['Extracted Seniority'] = section_content
            elif section_name == 'Extracted Industry':
                if not section_content.startswith('No'):
                    # Store industry
                    extracted_data['Extracted Industry'] = section_content
            elif section_name == 'Extracted Expertise':
                if not section_content.startswith('No'):
                    # Store expertise
                    extracted_data['Extracted Expertise'] = section_content
            elif section_name == 'Extracted Location':
                    # Store location
                    extracted_data['Extracted Location'] = section_content
            elif section_name == 'Extracted English Level':
                if not section_content.startswith('No'):
                    # Store English level
                    extracted_data['Extracted English Level'] = section_content
            elif section_name == 'Reasoning':
                if not section_content.startswith('No'):
                    # Store reasoning
                    extracted_data['Vacancy Reasoning'] = section_content

    return extracted_data

list_of_existing_roles = [
    "AI Solution Architect",
    "AI Engineer",
    "ASR Engineer",
    "Big Data Engineer",
    "C++ Developer",
    "Chatbot Developer",
    "CV Engineer",
    "Data Analyst",
    "Data Engineer",
    "Data Lead",
    "Data Scientist",
    "Web Scraping Specialist" ,
    "DL Engineer",
    "UX/UI Designer",
    "DevOps Engineer",
    "Engineering Manager",
    "FrontEnd Developer",
    "FullStack Web Developer",
    "Go Developer" ,
    "Java Developer",
    "LLM Engineer",
    "ML Researcher",
    "MLOps Engineer",
    "ML Engineer",
    "NLP Engineer",
    "Project Manager",
    "Python Developer",
    "React Developer",
    "Scala Developer",
    #- Software Engineer
    "System Architect",
    "Tech Lead",
    "iOS Developer",
    "Product Designer"
]

def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
    """
    Extracts key information from the vacancy description using the language model (LLM).

    Args:
    - vacancy (str): The vacancy description.
    - llm_handler (LLMHandler): Handler for interacting with the language model.

    Returns:
    - dict: A dictionary containing the extracted information.
    """
    existing_roles = ", ".join(list_of_existing_roles)

    # Define the prompt for the language model
    prompt = [
        {
            "role": "system",
            "content": "You are an expert in analyzing job descriptions."
        },
        {
            "role": "user",
            "content": (
                f"Your task is to process the provided job description and extract the following information:\n\n"
                f"1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
                f"Explain how you inferred the seniority level, role, programming languages, technologies, english level, industry, expertise and location. "
                f"If specific libraries or frameworks are mentioned, deduce the programming languages from them.\n"
                f"2. Identify the seniority level described in the job description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
                f"A 'Senior' should be a specialist with at least three years of experience. "
                f"Only 'Senior' can be a Lead or develop system-level architecture. "
                f"Consider adjectives like 'крутой', 'cool', or 'strong' as indicators of higher seniority 'Senior'."
                f"If no seniority level is explicitly mentioned, infer it from the context. If unsure, return 'Any'.\n"
                f"3. Identify the role described in the job description. The role should not include seniority. Compare the role with the following list of existing roles: {existing_roles}. "
                f"Select all approximately matching roles from the list and list them each on a new line with a dash. If there are no matches at all, write 'NEW' followed by the role extracted from the vacancy.\n"
                f"4. Extract the key programming languages mentioned in the job description and list them each on a new line. "
                f"If no programming languages are explicitly mentioned, infer them from the technologies or libraries listed. "
                f"If no programming languages are found, return 'No programming languages are found'.\n"
                f"5. Extract the key technologies mentioned in the job description and list them each on a new line. "
                f"If a technology has a commonly recognized abbreviation, return the full name followed by the abbreviation in parentheses. "
                f"If no technologies are found, return 'No technologies are found'.\n"
                f"6. Identify the required level of English mentioned in the job description. If no English level is found, return 'No English level is found'.\n"
                f"7. Identify the industry mentioned in the job description. If no industry is found, return 'No industry is found'.\n"
                f"8. Identify the expertise required in the job description. If no expertise is found, return 'No expertise is found'.\n"
                f"9. Identify the location mentioned in the job description. 'Remote' stands for 'Any location'"
                f"Write the location in English and without abbreviations. For example, if 'ЕС' or 'Европа' is mentioned, write 'European Union'. "
                f"If multiple countries are mentioned, list them separated by commas, for example, 'Only Poland and Romania' should be written as 'Poland, Romania'. "
                f"If countries to exclude are mentioned, prefix them with 'NOT ', for example, 'except Russia and Ukraine' should be written as 'NOT Russia, NOT Ukraine' "
                "and 'NO RF/RB' should be written as 'NOT Russia, Belarus'. Emojis like ❌ should be interpreted as 'NOT'."
                f"Note that 'RF' stands for Russia and 'RB' stands for Belarus."
                f"If the location is a specific city, write the city name first followed by the country, separated by a comma."
                f"Choose the broader geographical coverage if multiple locations are mentioned, for example, if it says 'EU, preferably Poland', then write 'European Union'. "
                f"If no location is found or if only the client's location is mentioned without implying the candidate's location, return 'Any location'.\n"
                f"If the location is mentioned in the context of the project description without implying the candidate's location, return 'Any location'."
                f"\n"
                f"The output should be formatted in Markdown with the following sections:\n"
                f"- **Reasoning**: The reasoning on how the information was extracted.\n"
                f"- **Extracted Seniority**: The seniority level extracted by the language model from the vacancy description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'.\n"
                f"Please consider Seniority at the upper limit, i.e. if it says 'Senior Principal', then it is 'Principal'\n"
                f"- **Extracted Role**: The role corresponding to the vacancy description extracted from the list of existing roles. If no matching role is found in the list, return 'NEW' followed by the role from the vacancy.\n"
                f"- **Extracted Programming Languages**: The programming languages extracted by the language model from the vacancy description. "
                f"If no programming languages are found, return 'No programming languages are found'. Each programming language should be listed on a new line.\n"
                f"- **Extracted Technologies**: The technologies extracted by the language model from the vacancy description. "
                f"If no technologies are found, return 'No technologies are found'. Each technology should be listed on a new line.\n"
                f"- **Extracted English Level**: The level of English extracted by the language model from the vacancy description. If no English level is found, return 'No English level is found'.\n"
                f"- **Extracted Industry**: The industry extracted by the language model from the vacancy description. If no industry is found, return 'No industry is found'.\n"
                f"- **Extracted Expertise**: The expertise extracted by the language model from the vacancy description. If no expertise is found, return 'No expertise is found'.\n"
                f"- **Extracted Location**: The location extracted by the language model from the vacancy description. "
                f"If no location is found, return 'Any location'.\n"
                f"\n"
                f"Here is an example:\n\n"
                f"# Example Input:\n"
                f"Американская компания в поиске опытного ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas.\n"
                f"\n"
                f"# Example Output:\n"
                f"- **Reasoning**: The job description mentions the need for an 'опытного' (experienced) ML Engineer, which indicates a 'Senior' level. The libraries PyTorch, TensorFlow, and pandas suggest the use of the Python programming language. The roles that match with the existing roles list include 'AI Engineer', 'Data Scientist', 'DL Engineer', 'ML Engineer' and 'ML Researcher' due to the overlap in required skills and technologies. The client location is US, but the candidate location is not specified. English level is not specified. No industry or expertise is mentioned.\n"
                f"- **Extracted Seniority**: Senior\n"
                f"- **Extracted Role**:\n"
                f"  - AI Engineer\n"
                f"  - Data Scientist\n"
                f"  - DL Engineer\n"
                f"  - ML Engineer\n"
                f"  - ML Researcher\n"
                f"- **Extracted Programming Languages**:\n"
                f"  - Python\n"
                f"- **Extracted Technologies**:\n"
                f"  - Machine Learning (ML)\n"
                f"  - Computer Vision (CV)\n"
                f"  - Natural Language Processing (NLP)\n"
                f"  - PyTorch\n"
                f"  - TensorFlow\n"
                f"  - Pandas\n"
                f"- **Extracted English Level**: No English level is found.\n"
                f"- **Extracted Industry**: No industry is found.\n"
                f"- **Extracted Expertise**: No expertise is found.\n"
                f"- **Extracted Location**: Any location\n"
                f"\n"
                f"Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\"\n"
                f"}}\n"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = max(len(vacancy) * 3, 500)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    # Replace all occurrences of "GoLang", "Golang" and "golang" with "Go"
    response = response.replace("GoLang", "Go").replace("Golang", "Go").replace("golang", "Go")

    # Parse the response from the LLM
    extracted_data = parse_llm_response(response)

    logger.info(f"extracted_data['Vacancy Reasoning'] : {extracted_data['Vacancy Reasoning']}")

    return extracted_data



