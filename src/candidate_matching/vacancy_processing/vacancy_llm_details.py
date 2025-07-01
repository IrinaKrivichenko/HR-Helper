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

            # Extract programming languages if present
            if section_name == 'Extracted Programming Languages':
                if not section_content.startswith('No'):
                    # Clean and store programming languages
                    languages = [lang.strip('- ').strip() for lang in section_content.split('\n') if lang.strip()]
                    extracted_data['Extracted Programming Languages'] = '\n'.join(languages)

            # Extract technologies if present
            elif section_name == 'Extracted Technologies':
                if not section_content.startswith('No'):
                    # Clean and store technologies
                    technologies = [tech.strip('- ').strip() for tech in section_content.split('\n') if tech.strip()]
                    extracted_data['Extracted Technologies'] = '\n'.join(technologies)

            # Extract role if present
            elif section_name == 'Extracted Role':
                if not section_content.startswith('No'):
                    # Store role
                    extracted_data['Extracted Role'] = section_content

            # Extract seniority if present
            elif section_name == 'Extracted Seniority':
                if not section_content.startswith('No'):
                    # Store seniority
                    extracted_data['Extracted Seniority'] = section_content

            # Extract industry if present
            elif section_name == 'Extracted Industry':
                if not section_content.startswith('No'):
                    # Store industry
                    extracted_data['Extracted Industry'] = section_content

            # Extract expertise if present
            elif section_name == 'Extracted Expertise':
                if not section_content.startswith('No'):
                    # Store expertise
                    extracted_data['Extracted Expertise'] = section_content

            # Extract English level if present
            elif section_name == 'Extracted English Level':
                if not section_content.startswith('No'):
                    # Store English level
                    extracted_data['Extracted English Level'] = section_content

            # Extract reasoning if present
            elif section_name == 'Reasoning':
                if not section_content.startswith('No'):
                    # Store reasoning
                    extracted_data['Vacancy Reasoning'] = section_content

            # Extract rate if present
            elif section_name == 'Extracted Rate':
                if not section_content.startswith('No'):
                    # Store rate
                    extracted_data['Extracted Rate'] = section_content

            # Extract reasoning about roles if present
            elif section_name == 'Reasoning about Roles':
                if not section_content.startswith('No'):
                    # Store reasoning about roles
                    extracted_data['Reasoning about Roles'] = section_content

            # Extract matched roles if present
            elif section_name == 'Matched Roles':
                # Filter out roles that start with "NEW" and clean the role names
                matched_roles = [
                    role.strip('- ').replace('-', '').strip()
                    for role in section_content.split('\n')
                    if role.strip() and not role.strip('- ').strip().startswith('NEW')
                ]
                # Join the matched roles with newlines and store them, or use an empty string if none are found
                extracted_data['Matched Roles'] = '\n'.join(matched_roles) if matched_roles else ''

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
    "C# Developers",
    ".Net Developers",
    "Product Designer"
]



def extract_vacancy_details(vacancy: str, llm_handler: LLMHandler, model="gpt-4o-mini"):
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
                "Your task is to process the provided job description and extract the following information:\n\n"
                "1. Reasoning: Provide a brief reasoning on how you extracted the information from the job description. "
                f"Explain how you inferred the programming languages, technologies, seniority level, role, English level, industry, expertise, location, and rate. "
                f"If specific libraries or frameworks are mentioned, deduce the programming languages from them.\n"
                "2. Extract the key programming languages mentioned in the job description and list them each on a new line. "
                f"If no programming languages are explicitly mentioned, infer them from the technologies or libraries listed. "
                f"If no programming languages are found, return 'No programming languages are found'.\n"
                "3. Extract the key technologies mentioned in the job description and list them each on a new line. "
                f"If a technology has a commonly recognized abbreviation, return the full name followed by the abbreviation in parentheses. "
                f"If no technologies are found, return 'No technologies are found'.\n"
                "4. Identify the seniority level described in the job description. "
                f"Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'. "
                f"A 'Senior' should be a specialist with at least three years of experience. "
                f"Only 'Senior' can be a Lead or develop system-level architecture. "
                f"Consider adjectives like 'крутой', 'cool', or 'strong' as indicators of higher seniority 'Senior'."
                f"If no seniority level is explicitly mentioned, infer it from the context. If unsure, return 'Any'.\n"
                "5. Identify the role described in the job description. The role should not include seniority. "
                f"Extract the role directly from the job description. If no role is found, return 'No role is found'.\n"
                "6. Identify the required level of English mentioned in the job description. The English level should be formatted as 'A1', 'B1', 'C1', etc. "
                f"Consider 'Fluent' as 'B2'. If a range is provided, such as 'B2-C1', return it as a range. If no English level is found, return 'No English level is found'.\n"
                "7. Identify the industry mentioned in the job description. If no industry is found or the industry is not in the list, return 'No industry is found'.\n"
                "8. Identify the expertise required in the job description. If no expertise is found, return 'No expertise is found'.\n"
                "9. Identify the rate or salary mentioned in the job description. The rate should be formatted as a number followed by a currency symbol and the period, for example, '10000$ per month'. "
                f"If a range is provided, such as '25-28$ per hour', return it as a range with the period. If phrases like 'up to' are used, extract the numerical value and assume it is per month unless otherwise specified. "
                f"If no rate or salary is found, return 'No rate is found'.\n"
                "10. Reasoning about Roles: Provide reasoning on which roles from the list of existing roles could be suitable for this job description. "
                f"Compare the extracted role with the following list of existing roles: {existing_roles}. "
                f"Explain why certain roles match based on the overlap in required skills and technologies.\n"
                "11. Matched Roles: List all approximately matching roles from the existing roles list, each on a new line with a dash. If there are no matches at all, write 'NEW' followed by the role extracted from the vacancy.\n"
                f"The output should be formatted in Markdown with the following sections:\n"
                "- **Reasoning**: The reasoning on how the information was extracted.\n"
                "- **Extracted Programming Languages**: The programming languages extracted by the language model from the vacancy description. Each programming language should be listed on a new line.\n"
                "- **Extracted Technologies**: The technologies extracted by the language model from the vacancy description. Each technology should be listed on a new line.\n"
                "- **Extracted Seniority**: The seniority level extracted by the language model from the vacancy description. Seniority level should be one of the following: 'Any', 'Junior', 'Middle', 'Senior', 'Principal'.\n"
                "- **Extracted Role**: The role corresponding to the vacancy description extracted directly from the job description.\n"
                "- **Extracted English Level**: The level of English extracted by the language model from the vacancy description.\n"
                "- **Extracted Industry**: The industry extracted by the language model from the vacancy description.\n"
                "- **Extracted Expertise**: The expertise extracted by the language model from the vacancy description.\n"
                "- **Extracted Rate**: The rate extracted by the language model from the vacancy description.\n"
                "- **Reasoning about Roles**: The reasoning on which roles from the list of existing roles could be suitable for this job description.\n"
                "- **Matched Roles**: The roles from the existing roles list that match the extracted role, each on a new line with a dash. If no matches are found, write 'NEW' followed by the role extracted from the vacancy.\n"
                f"\n"
                "Here is an example:\n\n"
                "# Example Input:\n"
                f"Американская компания в поиске опытного ML Engineer на группу проектов, представляющих собой различные AI решения (проекты в разных сферах, от Computer Vision до NLP). Со знанием библиотек PyTorch, TensorFlow, pandas. Уровень английского: C1. Зарплата - до 8000-10000$ gross.\n"
                f"\n"
                "# Example Output:\n"
                "- **Reasoning**: The job description mentions the need for an 'опытного' (experienced) ML Engineer, which indicates a 'Senior' level. The libraries PyTorch,TensorFlow, and Pandas suggest the use of the Python programming language. The role in the vacancy is 'ML Engineer'. The salary mentioned is up to 8000-10000$ gross, which is interpreted as 8000-10000$ per month. The English level mentioned is C1. No industry or expertise is mentioned.\n"
                "- **Extracted Programming Languages**:\n"
                f"  - Python\n"
                "- **Extracted Technologies**:\n"
                f"  - Machine Learning (ML)\n"
                f"  - Computer Vision (CV)\n"
                f"  - Natural Language Processing (NLP)\n"
                f"  - PyTorch\n"
                f"  - TensorFlow\n"
                f"  - Pandas\n"
                "- **Extracted Seniority**: Senior\n"
                "- **Extracted Role**: ML Engineer\n"
                "- **Extracted English Level**: C1\n"
                "- **Extracted Industry**: No industry is found\n"
                "- **Extracted Expertise**: No expertise is found\n"
                "- **Extracted Location**: Any location\n"
                "- **Extracted Rate**: 8000-10000$ per month\n"
                "- **Reasoning about Roles**: The role of \"ML Engineer\" requires a strong background in machine learning, as evidenced by the need for experience with libraries such as PyTorch, TensorFlow, and Pandas, which are commonly used in machine learning and data analysis tasks, supports this match. Additionally, the role involves working on projects related to Computer Vision (CV) and Natural Language Processing (NLP). AI Engineer: This role is a good match because AI Engineers often work on similar technologies and projects involving machine learning and artificial intelligence. They typically have experience with the same libraries and frameworks mentioned in the job description. Data Scientist: Data Scientists also work extensively with machine learning models and data analysis, making this role a suitable match. They often use similar tools and techniques to extract insights and build predictive models. DL Engineer: Deep Learning Engineers specialize in developing and implementing deep learning models, which aligns well with the requirements of this job description. Their expertise in deep learning frameworks like PyTorch and TensorFlow is particularly relevant. ML Researcher: ML Researchers focus on advancing the field of machine learning through research and development. Their deep understanding of machine learning algorithms and techniques makes them a good fit for this role. CV Engineer: Given the mention of Computer Vision in the job description, a CV Engineer, who specializes in this area, is a relevant match. NLP Engineer: Similarly, the mention of Natural Language Processing tasks makes an NLP Engineer a suitable match for this role.\n"
                "- **Matched Roles**:\n"
                f"  - AI Engineer\n"
                f"  - CV Engineer\n"
                f"  - Data Scientist\n"
                f"  - DL Engineer\n"
                f"  - ML Engineer\n"
                f"  - NLP Engineer\n"
                f"  - ML Researcher\n"
                "\n"                
                "Here is the input:\n\n"
                f"# Job Description:\n"
                f"{vacancy}\"\n"
            )
        }
    ]

    # Calculate max tokens based on the length of the vacancy description
    max_tokens = max(len(vacancy) * 3, 500)
    # Send the prompt to the LLM handler and get the response
    response = llm_handler.get_answer(prompt, model=model, max_tokens=max_tokens)

    response = response.replace("GoLang", "Go").replace("Golang", "Go").replace("golang", "Go")
    response = response.replace("- GitHub\n", "").replace("- Github\n", "").replace("- Git\n", "")
    response = response.replace("- GitLab\n", "").replace("- Gitlab\n", "")

    # Parse the response from the LLM
    extracted_data = parse_llm_response(response)

    return extracted_data



