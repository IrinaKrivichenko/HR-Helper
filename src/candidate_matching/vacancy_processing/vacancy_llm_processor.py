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
                    extracted_data['Extracted Role'] = section_content
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
                if not section_content.startswith('No'):
                    # Store location
                    extracted_data['Extracted Location'] = section_content
            elif section_name == 'Extracted English Level':
                if not section_content.startswith('No'):
                    # Store English level
                    extracted_data['Extracted English Level'] = section_content
            elif section_name == 'Reasoning':
                if not section_content.startswith('No'):
                    # Store reasoning
                    extracted_data['Reasoning'] = section_content

    return extracted_data

def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
    """
    Extracts key information from the vacancy description using the language model (LLM).

    Args:
    - vacancy (str): The vacancy description.
    - llm_handler (LLMHandler): Handler for interacting with the language model.

    Returns:
    - dict: A dictionary containing the extracted information.
    """

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
                f"2. Extract the key programming languages mentioned in the job description and list them each on a new line. "
                f"If no programming languages are explicitly mentioned, infer them from the technologies or libraries listed. "
                f"If no programming languages are found, return 'No programming languages are found'.\n"
                f"3. Extract the key technologies mentioned in the job description and list them each on a new line. "
                f"If a technology has a commonly recognized abbreviation, return the full name followed by the abbreviation in parentheses. "
                f"If no technologies are found, return 'No technologies are found'.\n"
                f"4. Identify the seniority level described in the job description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
                f"If no seniority level is explicitly mentioned, infer it from the context. If unsure, return 'Any'.\n"
                f"5. Identify the role described in the job description. If no role is found, return 'No role is found'.\n"
                f"6. Identify the industry mentioned in the job description. If no industry is found, return 'No industry is found'.\n"
                f"7. Identify the expertise required in the job description. If no expertise is found, return 'No expertise is found'.\n"
                f"8. Identify the location mentioned in the job description. Note that 'RF' stands for Russian Federation and 'RB' stands for Republic of Belarus. "
                f"If no location is found, return 'No location is found'.\n"
                f"9. Identify the required level of English mentioned in the job description. If no English level is found, return 'No English level is found'.\n"
                f"\n"
                f"The output should be formatted in Markdown with the following sections:\n"
                f"- **Reasoning**: The reasoning on how the information was extracted.\n"
                f"- **Extracted Seniority**: The seniority level extracted by the language model from the vacancy description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'.\n"
                f"- **Extracted Role**: The role extracted by the language model from the vacancy description. If no role is found, return 'No role is found'.\n"
                f"- **Extracted Programming Languages**: The programming languages extracted by the language model from the vacancy description. "
                f"If no programming languages are found, return 'No programming languages are found'. Each programming language should be listed on a new line.\n"
                f"- **Extracted Technologies**: The technologies extracted by the language model from the vacancy description. "
                f"If no technologies are found, return 'No technologies are found'. Each technology should be listed on a new line.\n"
                f"- **Extracted English Level**: The level of English extracted by the language model from the vacancy description. If no English level is found, return 'No English level is found'.\n"
                f"- **Extracted Industry**: The industry extracted by the language model from the vacancy description. If no industry is found, return 'No industry is found'.\n"
                f"- **Extracted Expertise**: The expertise extracted by the language model from the vacancy description. If no expertise is found, return 'No expertise is found'.\n"
                f"- **Extracted Location**: The location extracted by the language model from the vacancy description. "
                f"If no location is found or if only the client's location is mentioned without implying the candidate's location, return 'No location is found'.\n"
                f"\n"
                f"Here is an example:\n\n"
                f"# Example Input:\n"
                f"Мы расширяем нашу команду и в поиске опытного ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas.\n"
                f"\n"
                f"# Example Output:\n"
                f"- **Reasoning**: The job description mentions the need for an 'опытного' (experienced) ML Engineer, which indicates a 'Senior' level. The libraries PyTorch, TensorFlow, and pandas suggest the use of the Python programming language. No industry or expertise is mentioned. The location and English level are not specified.\n"
                f"- **Extracted Seniority**: Senior\n"
                f"- **Extracted Role**: ML Engineer\n"
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
                f"- **Extracted Location**: No location is found.\n"
                f"\n"
                f"Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\"\n"
                f"}}\n"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = len(vacancy) * 3
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    # Log the response
    logger.info(response)

    # Parse the response from the LLM
    extracted_data = parse_llm_response(response)

    return extracted_data



# from src.logger import logger
# from src.nlp.llm_handler import LLMHandler
#
#
# def parse_llm_response(response: str) -> dict:
#     extracted_data = {}
#     # Split the response into sections
#     sections = response.split('- **')
#     for section in sections:
#         if ':' in section:
#             section_name, section_content = section.split('**:', 1)
#             section_name = section_name.strip()
#             section_content = section_content.strip()
#             if section_name == 'Extracted Technologies':
#                 if not section_content.startswith('No'):
#                     technologies = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
#                     extracted_data['Extracted Technologies'] = '\n'.join(technologies)
#             elif section_name == 'Extracted Role':
#                 if not section_content.startswith('No'):
#                     extracted_data['Extracted Role'] = section_content
#             elif section_name == 'Extracted Industry':
#                 if not section_content.startswith('No'):
#                     extracted_data['Extracted Industry'] = section_content
#             elif section_name == 'Extracted Expertise':
#                 if not section_content.startswith('No'):
#                     extracted_data['Extracted Expertise'] = section_content
#             elif section_name == 'Extracted Location':
#                 if not section_content.startswith('No'):
#                     extracted_data['Extracted Location'] = section_content
#     return extracted_data
#
#
# def extract_vacancy_info(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
#     """
#     Extracts key information from the vacancy description using the language model (LLM).
#
#     Args:
#     - vacancy (str): The vacancy description.
#     - llm_handler (LLMHandler): Handler for interacting with the language model.
#
#     Returns:
#     - dict: A dictionary containing the extracted information.
#     """
#
#     prompt = [
#         {
#             "role": "system",
#             "content": "You are an expert in analyzing job descriptions."
#         },
#         {
#             "role": "user",
#             "content": (
#                 f"Your task is to process the provided job description and extract the following information:\n\n"
#                 f"1. Extract the key technologies mentioned in the job description and list them each on a new line. If a technology has a commonly recognized abbreviation (e.g., Artificial Intelligence = AI, Amazon Web Services = AWS), return the full name followed by the abbreviation in parentheses. Also when extracting key technologies from the job description, make sure you check not only the body text but also the role title. Some technologies may only be mentioned in the role title, such as 'PHP Dev', 'Java Developer', '.NET Engineer', etc. Make sure these technologies are also extracted and included in the list of technologies.\n"
#                 f"2. Identify the role described in the job description.\n"
#                 f"3. Identify the industry mentioned in the job description.\n"
#                 f"4. Identify the expertise required in the job description.\n"
#                 f"5. Identify the location mentioned in the job description. Note that 'RF' stands for Russian Federation and 'RB' stands for Republic of Belarus.\n"
#                 f"\n"
#                 f"The output should be formatted in Markdown with the following sections:\n"
#                 f"- **Extracted Technologies**: The technologies extracted by the language model from the vacancy description (use full names followed by abbreviations in parentheses if applicable). If no technologies are found, return 'No technologies are found'. Each technology should be listed on a new line.\n"
#                 f"- **Extracted Role**: The role extracted by the language model from the vacancy description. If no role is found, return 'No role is found'.\n"
#                 f"- **Extracted Industry**: The industry extracted by the language model from the vacancy description. If no industry is found, return 'No industry is found'.\n"
#                 f"- **Extracted Expertise**: The expertise extracted by the language model from the vacancy description. If no expertise is found, return 'No expertise is found'.\n"
#                 f"- **Extracted Location**: The location extracted by the language model from the vacancy description. If no location is found, return 'No location is found'.\n"
#                 f"\n"
#                 f"Here is an example:\n\n"
#                 f"# Example Input:\n"
#                 f"Мы расширяем нашу команду и в поиске Senior ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas\n"
#                 f"\n"
#                 f"# Example Output:\n"
#                 f"- **Extracted Technologies**:\n"
#                 f"  - Machine Learning (ML)\n"
#                 f"  - Computer Vision (CV)\n"
#                 f"  - Natural Language Processing (NLP)\n"
#                 f"  - PyTorch\n"
#                 f"  - TensorFlow\n"
#                 f"  - Pandas\n\n"
#                 f"- **Extracted Role**: Senior ML Engineer\n\n"
#                 f"- **Extracted Industry**: No industry is found.\n\n"
#                 f"- **Extracted Expertise**: No expertise is found.\n\n"
#                 f"- **Extracted Location**: No location is found.\n\n"
#                 f"\n"
#                 f"Here is the input:\n\n"
#                 f"# Job Description:\n"
#                 f"{vacancy}\"\n"
#                 f"}}\n"
#             )
#         }
#     ]
#
#     max_tokens = len(vacancy)*3
#     # Send the prompt to the LLM handler and get the response
#     response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)
#
#     logger.info(response)
#
#     # Parse the response from the LLM
#     extracted_data = parse_llm_response(response)
#
#     return extracted_data
#
#
