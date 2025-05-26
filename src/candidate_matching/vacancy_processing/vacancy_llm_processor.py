from src.nlp.llm_handler import LLMHandler


def parse_llm_response(response: str) -> dict:
    extracted_data = {}
    # Split the response into sections
    sections = response.split('- **')
    for section in sections:
        if ':' in section:
            section_name, section_content = section.split('**:', 1)
            section_name = section_name.strip()
            section_content = section_content.strip()
            if section_name == 'Extracted Technologies':
                if not section_content.startswith('No'):
                    technologies = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
                    extracted_data['Extracted Technologies'] = '\n'.join(technologies)
            elif section_name == 'Extracted Role':
                if not section_content.startswith('No'):
                    extracted_data['Extracted Role'] = section_content
            elif section_name == 'Extracted Industry':
                if not section_content.startswith('No'):
                    extracted_data['Extracted Industry'] = section_content
            elif section_name == 'Extracted Expertise':
                if not section_content.startswith('No'):
                    extracted_data['Extracted Expertise'] = section_content
            elif section_name == 'Extracted Location':
                if not section_content.startswith('No'):
                    extracted_data['Extracted Location'] = section_content
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

    prompt = [
        {
            "role": "system",
            "content": "You are an expert in analyzing job descriptions."
        },
        {
            "role": "user",
            "content": (
                f"Your task is to process the provided job description and extract the following information:\n\n"
                f"1. Extract the key technologies mentioned in the job description and list them each on a new line. If a technology has a commonly recognized abbreviation (e.g., Artificial Intelligence = AI, Amazon Web Services = AWS), return the full name followed by the abbreviation in parentheses.\n"
                f"2. Identify the role described in the job description.\n"
                f"3. Identify the industry mentioned in the job description.\n"
                f"4. Identify the expertise required in the job description.\n"
                f"5. Identify the location mentioned in the job description. Note that 'RF' stands for Russian Federation and 'RB' stands for Republic of Belarus.\n"
                f"\n"
                f"The output should be formatted in Markdown with the following sections:\n"
                f"- **Extracted Technologies**: The technologies extracted by the language model from the vacancy description (use full names followed by abbreviations in parentheses if applicable). If no technologies are found, return 'No technologies are found'. Each technology should be listed on a new line.\n"
                f"- **Extracted Role**: The role extracted by the language model from the vacancy description. If no role is found, return 'No role is found'.\n"
                f"- **Extracted Industry**: The industry extracted by the language model from the vacancy description. If no industry is found, return 'No industry is found'.\n"
                f"- **Extracted Expertise**: The expertise extracted by the language model from the vacancy description. If no expertise is found, return 'No expertise is found'.\n"
                f"- **Extracted Location**: The location extracted by the language model from the vacancy description. If no location is found, return 'No location is found'.\n"
                f"\n"
                f"Here is an example:\n\n"
                f"# Example Input:\n"
                f"Мы расширяем нашу команду и в поиске Senior ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas\n"
                f"\n"
                f"# Example Output:\n"
                f"- **Extracted Technologies**:\n"
                f"  - Machine Learning (ML)\n"
                f"  - Computer Vision (CV)\n"
                f"  - Natural Language Processing (NLP)\n"
                f"  - PyTorch\n"
                f"  - TensorFlow\n"
                f"  - Pandas\n\n"
                f"- **Extracted Role**: Senior ML Engineer\n\n"
                f"- **Extracted Industry**: No industry is found.\n\n"
                f"- **Extracted Expertise**: No expertise is found.\n\n"
                f"- **Extracted Location**: No location is found.\n\n"
                f"\n"
                f"Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\"\n"
                f"}}\n"
            )
        }
    ]

    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=500)

    print(response)

    # Parse the response from the LLM
    extracted_data = parse_llm_response(response)

    return extracted_data


