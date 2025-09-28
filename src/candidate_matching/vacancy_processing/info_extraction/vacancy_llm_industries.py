from src.google_services.sheets import read_specific_columns
from src.data_processing.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler


def parse_llm_vacancy_industries_response(response: str, add_tokens_info: bool) -> dict:
    # Initialize a dictionary to store extracted data
    extracted_data = {}

    # Split the response into sections
    sections = response.split('##')

    # Iterate over each section to extract relevant information
    for section in sections:
        if ':' in section:
            # Split section into name and content
            section_name, section_content = section.split(':', 1)
            section_name = section_name.strip()
            section_content = section_content.strip()

            # Extract industries if present
            if section_name == 'Extracted Industries':
                    # Store industries
                    # extracted_data['Extracted Industries'] = section_content
                    industries = [
                        role.strip('- ').replace('-', '').strip()
                        for role in section_content.split('\n')
                        if role.strip() and not role.strip('- ').strip().startswith('NEW')
                    ]
                    # Join the matched roles with newlines and store them, or use an empty string if none are specified
                    extracted_data['Extracted Industries'] = '\n'.join(industries) if industries else ''

            # Extract reasoning if present
            elif section_name == 'Reasoning':
                    # Store reasoning
                    extracted_data['Vacancy Reasoning'] = section_content

            # Parse token usage and cost information
            elif section_name == 'Token Usage and Cost':
                print("add_tokens_info", add_tokens_info)
                token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_industries", add_tokens_info=add_tokens_info)
                extracted_data.update(token_data)

    return extracted_data




def extract_vacancy_industries(vacancy: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):
    industries_list = list(read_specific_columns(['Industries Values'], 'values')['Industries Values'])
    industries = {'", "'.join(industries_list)}
    industries = f'"{industries}"'

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
                "1. **Reasoning**: Provide a brief explanation of how you extracted the information from the job description. "
                "Explain how you inferred the industries. If the job description does not explicitly mention a specific industries from the list, "
                "then conclude that no industries is specified.\n"
                "2. **Industries Identification**: Identify all possible industries mentioned in the job description. Select the industries only from the following list: "
                f"{industries}. \n\n"
                "When identifying industries:"
                "1. Pay attention to explicit mentions of industries in the job description."
                "2. If the job description includes preferences or requirements for experience or knowledge in a specific industry, include that industry in the extracted list, even if it is not the primary focus of the role."
                "3. If no industries are explicitly mentioned or none of the identified industries are in the list, return 'No industry is specified'."

                "Format the output in Markdown with the following sections:\n"
                "## Reasoning: The reasoning on how the information was extracted.\n"
                "## Extracted Industries: The industries extracted by the language model from the vacancy description.\n"
                "\n"
                "Here are some examples:\n\n"
                "# Example 1:\n"
                "We are seeking an experienced Web Developer to join our dynamic team, supporting the creation and deployment of a cutting-edge website for our expanding network of eateries across 30+ divisions in the EU. Your primary focus will be on designing and implementing a user-friendly and efficient online platform that enhances our production and delivery services. You will work closely with our cross-functional teams to ensure high-quality digital solutions that meet the needs of our diverse customer base. Salary - up to 5000$ gross.\n"
                "\n"
                "## Reasoning: The industries related to this project are Retail, Logistics, Manufacturing, and E-commerce.\n"
                "## Extracted Industries: \n"
                "  - Retail\n"
                "  - Logistics\n"
                "  - Manufacturing\n"
                "  - E-commerce\n"
                "\n"
                "# Example 2:\n"
                "We are looking for a Senior Front-End Developer to join our team. Candidates must not be located in Russia, Ukraine, or Belarus due to current operational constraints.\n"
                "\n"
                "## Reasoning: The job description does not mention any specific industry, so no industry is identified.\n"
                "## Extracted Industries:\n"
                "  - No industry is specified\n"
                "\n"
                "# Example 3:\n"
                "Location: Remote (within Europe). We are seeking a skilled Data Analyst to join our retail team. The role involves analyzing data trends and providing insights to support business decisions across our European markets.\n"
                "\n"
                "## Reasoning: The mention of joining a 'retail team' suggests the industry is Retail.\n"
                "## Extracted Industries:\n"
                "  - Retail\n"
                "\n"
                "# Example 4:\n"
                "We are seeking a skilled Cloud Engineer with experience in cloud infrastructure, cloud-native software engineering, security, and open-source contributions. Technologies include Kubernetes, Docker, and cloud hyperscalers (AWS, Azure, GCP).\n\n"
                "## Reasoning:\n"
                "The job description focuses on technologies and skills related to cloud infrastructure without explicitly mentioning a specific industry from the list.\n"
                "## Extracted Industries:\n"
                "  - No industry is specified\n"
                "\n"
                "# Example 5:\n"
                "Добрый день! Мы в поиске Senior AI\Python developer\n Requirements:\n- 5+ years of experience in AI/ML development\n- Strong background in generative AI, LLM fine-tuning, or AI-powered RAG systems.\n- Proficiency in Python, PyTorch, TensorFlow, and Hugging Face.\n- Expertise in LLM architectures (GPT, LLaMA, Mistral, etc.) and vector search (FAISS, Pinecone, Weaviate).\n- Knowledge of graph-based AI (Neo4j, AWS Neptune).\n- Experience conducting feature engineering, dimensionality reduction, and statistical inference on biological data.\n- Familiarity with cloud services (AWS, GCP) and MLOps (Docker, Kubernetes, CI/CD for AI models).\n- A strong grasp of genomics and bioinformatics is a major plus.\n\n"
                "## Reasoning:\n"
                "The job description mentions biological data, genomics, and bioinformatics, which are key indicators of the Healthcare and Biotechnology industries.\n"
                "## Extracted Industries\n"
                "  - Healthcare\n"
                "  - Biotechnology\n"
                "Here are some examples:\n\n"
                "# Example 6:\n"
                "We are looking for an experienced AI Transformation Specialist to support a large-scale AI transformation project. The role involves data engineering, ML model deployment, cloud experience (preferably GCP), and productionalization of AI/ML use cases. Experience in banking or insurance is a plus.\n"
                "\n"
                "## Reasoning:\n"
                "The job description mentions supporting an AI transformation project, with specific references to data engineering, ML model deployment, cloud experience (preferably GCP), and AI/ML use case productionalization. It also notes that experience in banking or insurance is a plus, which are industries related to financial services. While the description focuses on AI, data engineering, and cloud technologies, which are cross-industry skills, the explicit mention of banking and insurance as relevant experience ties the role to the Financial Services and Insurance industries.\n"
                "## Extracted Industries:\n"
                "  - Financial Services\n"
                "  - Insurance\n"
                "# Example 7:\n"
                "We are seeking an Application Developer to work on an 'Aviation Messaging' project, focusing on the integration layer for aviation systems. Responsibilities include supporting aviation messaging applications, designing Java-based integration interfaces, and collaborating with teams in Hungary and Germany. The role involves working with technologies such as Linux, SQL, Git, Maven, and Apache Camel/Karaf.\n"
                "\n"
                "## Reasoning:\n"
                "The job description specifies a position related to 'Aviation Messaging' and mentions working on an 'Integration layer for aviation systems.' The responsibilities include supporting aviation messaging applications and designing Java-based integration interfaces, which are typical in the telecommunications sector due to the focus on messaging systems and data exchange. Additionally, the mention of aviation systems could suggest a connection to industries like Automotive Manufacturing, as aviation and automotive industries often share overlapping technologies and integration practices. Based on this reasoning, the extracted industries are Telecommunications and Automotive Manufacturing.\n"
                "## Extracted Industries:\n"
                "  - Telecommunications\n"
                "  - Automotive Manufacturing\n"
                "# Example 8:\n"
                "We are seeking an Embedded Software Engineer to work on software development for EV charging stations. The role involves implementing protocols for EV charging standards (GB/T, CHAdeMO, CCS), working with microcontrollers (STM32), and integrating with battery management systems (BMS). Responsibilities include ensuring compliance with EV charging protocols and optimizing energy efficiency during charging sessions.\n"
                "\n"
                "## Reasoning:\n"
                "The job description focuses on embedded software development for charging stations, specifically mentioning protocols related to electric vehicle (EV) charging standards (GB/T, CHAdeMO, CCS), microcontrollers (STM32), and integration with battery management systems (BMS). These details point towards the automotive industry, particularly the electric vehicle charging infrastructure segment. Additionally, the focus on optimizing energy efficiency and the integration of charging stations with energy systems strongly ties the project to the Energy industry. Since the description explicitly references EV charging stations and protocols specific to EV standards, the extracted industries are Automotive Manufacturing and Energy.\n"
                "## Extracted Industries:\n"
                "  - Automotive Manufacturing\n"
                "  - Energy\n"
                "# Example 9:"
                "We are seeking a team to transform how organizational knowledge is captured, structured, and delivered using AI/ML and Generative AI technologies. Key objectives include automating processes (classification, summarization, and knowledge extraction), building and testing AI/ML prototypes, and developing scalable solutions that enhance consultant productivity. There is a strong emphasis on driving adoption of new formats of knowledge capture beyond traditional document-based approaches."
                "## Reasoning:"
                "The job description focuses on transforming organizational knowledge and enhancing consultant productivity, which are key aspects of management and organizational optimization. The emphasis on automating processes and improving knowledge capture aligns with the goals of the Management industry. No other industries from the provided list are explicitly mentioned or strongly implied."
                "## Extracted Industries:\n"
                "  - Management\n"
                "# Example 10:"
                "BioCatch is the leader in Behavioral Biometrics, a technology that leverages machine learning to analyze an online user’s physical and cognitive digital behavior to protect individuals online."
                "## Reasoning:"
                "The job description highlights the use of behavioral biometrics to analyze user behavior and protect individuals online. This directly relates to the Cybersecurity industry, as the primary focus is on fraud prevention and online protection. Additionally, behavioral biometrics is widely used in financial services to prevent fraud and secure digital transactions, which ties the project to the Financial Services industry."
                "## Extracted Industries:"
                "  - Cybersecurity\n"
                "  - Financial Services\n"

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
    extracted_data = parse_llm_vacancy_industries_response(response, add_tokens_info=add_tokens_info)

    return extracted_data

