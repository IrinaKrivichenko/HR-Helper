from src.nlp.llm_handler import parse_token_usage_and_cost, LLMHandler

def parse_llm_vacancy_location_response(response: str, add_tokens_info: bool) -> dict:
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

            # Extract location if present
            if section_name == "Candidate's Location":
                # Store location
                if "remote" in section_content.strip().lower():
                    section_content = "Any location"
                extracted_data['Extracted Location'] = section_content

            # Extract reasoning if present
            elif section_name == 'Reasoning':
                if not section_content.startswith('No'):
                    # Store reasoning
                    extracted_data['Vacancy Reasoning'] = section_content

            # Parse token usage and cost information
            elif section_name == 'Token Usage and Cost':
                print("add_tokens_info", add_tokens_info)
                token_data = parse_token_usage_and_cost(section_content, additional_key_text=" vacancy_location", add_tokens_info=add_tokens_info)
                extracted_data.update(token_data)

    return extracted_data


def extract_vacancy_location(vacancy: str, llm_handler: LLMHandler, model="gpt-4.1-nano", add_tokens_info: bool = False):

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
                "Explain how you inferred the preferred candidate's location.\n"
                "2. Identify the candidate's location mentioned in the job description. "
                "Write the location in English and without abbreviations. For example, if 'ЕС' or 'Европа' is mentioned, write 'European Union'. "
                "If multiple countries are mentioned, list them separated by commas, for example, 'Only Poland and Romania' should be written as 'Poland, Romania'. "
                "If countries to exclude are mentioned, prefix them with 'NOT ', for example, 'except Russia and Ukraine' should be written as 'NOT Russia, NOT Ukraine'. "
                "Emojis like ❌ should be interpreted as 'NOT', for example, '❌ RF/RB' should be written as 'NOT Russia, NOT Belarus'. "
                "Note that 'RF' stands for Russia and 'RB' stands for Belarus."
                "If the location is a specific city, write the city name first followed by the country, separated by a comma."
                "Choose the broader geographical coverage if multiple locations are mentioned, for example, if it says 'EU, preferably Poland', then write 'European Union'. "
                "If no location is found or if only the client's location is mentioned without implying the candidate's location, return 'Remote'.\n"
                "If the location is mentioned in the context of the project description without implying the candidate's location, return 'Remote'.\n"
                "\n"
                "The output should be formatted in Markdown with the following sections:\n"
                "## Reasoning: The reasoning on how the information was extracted.\n"
                "## Candidate's Location: The location extracted by the language model from the vacancy description.\n"
                "\n"
                "Here are some examples:\n\n"
                "# Example 1 Input:\n"
                "We are seeking an experienced Web Developer to join our dynamic team, supporting the creation and deployment of a cutting-edge website for our expanding major banking group across 30+ subsidiaries in the EU. Your primary focus will be on designing and implementing a user-friendly and efficient online platform. You will work closely with our cross-functional teams to ensure high-quality digital solutions that meet the needs of our diverse customer base. Salary - up to 5000$ gross.\n"
                "\n"
                "## Reasoning: The job description specifies that the project supports a major banking group across '30+ subsidiaries in the EU,' indicating that the client operates within the European Union. However, the description emphasizes collaboration with technical teams and data management, which are activities that can be performed remotely. There is no explicit mention of a required candidate location, nor are there any restrictions or preferences for specific countries. The absence of location constraints and the nature of the tasks suggest that the candidate can work remotely, regardless of their specific location within or outside the EU.\n"
                "## Candidate's Location: Remote\n"
                "\n"
                "# Example 2 Input:\n"
                "We are looking for a Senior Front-End Developer to join our team. Any location – Open to all countries RU, UA, or BY due to current operational constraints.\n"
                "\n"
                "## Reasoning: The job description explicitly states 'Any location – Open to all countries except RU, UA, or BY,' indicating that candidates from all countries are eligible except those from Russia, Ukraine, and Belarus. The phrase 'Any location' typically suggests a remote or globally accessible position. However, the explicit exclusion of Russia, Ukraine, and Belarus means that while the position is open to candidates from any other country, it is not available to those based in these excluded countries. Therefore, the location should be summarized with the specific exclusions mentioned."
                "## Candidate's Location: NOT Russia, NOT Ukraine, NOT Belarus\n"
                "\n"
                "# Example 3 Input:\n"
                "Location: Remote (within Europe). We are seeking a skilled Data Analyst to join our retail team. The role involves analyzing data trends and providing insights to support business decisions across our European markets.\n"
                "\n"
                "## Reasoning: The job description specifies that the location is 'Remote (within Europe)', indicating that the candidate must be located within Europe but can work remotely from any European country.\n"
                "## Candidate's Location: European Union\n"
                "\n"
                "# Example 4 Input:\n"
                "Tech: Node + React + TypeScript on AWS with PostgreSQL core  \nEnglish: B2  \nExperience: Senior  \nLocation: Any except Cyprus and Israel   \nProject: All in one cloud-based platform that enables businesses to manage operations  \n"
                "\n"
                "## Reasoning: The job description explicitly states \"Location: Any except Cyprus and Israel,\" which indicates that candidates should not be located in these countries, Since no other specific location is mentioned, and the project involves developing a smartwatch app with no geographical restrictions specified for the candidate, the safest inference is that the position is open to candidates outside Cyprus and Israel, potentially globally, The mention of \"Детали в лс\" (details in private message) suggests that further specifics might be provided privately, but based solely on the provided text, the location restriction is clear, Therefore, the extracted location is \"NOT Cyprus, NOT Israel,\"\n"
                "## Candidate's Location: NOT Cyprus, NOT Israel\n"
                "\n"
                "# Example 5 Input:\n"
                "Senior/Lead Flutter Developer (Frontend)  \nПроект: messaging platform  \nДлительность: 3+ months, fulltime  \nКлиент: EU  \nAнглийский: В2 и выше  \nЛокация: EU (желательно Польша, Варшава)  \n"
                "\n"
                "## Reasoning: The job description explicitly mentions the location as \"EU (желательно Польша, Варшава)\", which indicates that the preferred location is Poland, specifically Warsaw, within the European Union, Since the description states \"желательно\" (preferably), it suggests that the candidate should ideally be located in Warsaw, Poland, but the broader location is the European Union, The mention of \"EU\" as the project client also supports the broader geographical scope, No other locations are specified or implied, and the role appears to be open to candidates within the EU, with a preference for Poland, Warsaw,\n"
                "## Candidate's Location: European Union, Poland, Warsaw\n"
                "\n"
                "# Example 6 Input:\n"
                "🔎Full-Stack Engineers \nStack: Go, ,NET, Node, TS, React, AWS \nNot looking for any specific language, but .NET and Golang developers tend to do best\nProject: Fintech/consumer app/crypto  \nVery interesting domain, including agentic AI, crypto, and a self-service B2B2C SaaS product\nDuration: 3+ months with extension for the best candidates out of the team of 12 people\nEngagement: Full-time\nRequirements: Math, algorithms, strong tech background, Polish and English are must-have,  \nLooking for solid experience with web technologies, backend, and any statically typed or functional language (Java, ,NET, Kotlin, Scala, Clojure, etc,)\n"
                "\n"
                "## Reasoning: The job description specifies that the candidate must speak Polish and English, which might suggest a connection to Poland or Polish-speaking markets. However, language requirements do not necessarily dictate the physical location of the role. The job description does not explicitly mention a specific city or geographical area, nor does it restrict the candidate's location to Poland. There is also no explicit mention of the need for the candidate to be on-site. Given the context and the nature of roles in the fintech/crypto industry, which often support remote work arrangements, the most logical inference is that the position can be performed remotely. The industry is clearly fintech/crypto, as indicated by the project description mentioning 'Fintech/consumer app/crypto' and related technologies like agentic AI and SaaS products, which are conducive to remote work environments.\n"
                "## Candidate's Location: Remote\n"
                "\n"
                "# Example 7 Input:\n"
                "We are looking for a Backend Developer with expertise in Java and Spring Boot. The role involves developing and maintaining robust server-side applications. Location: except for Portugal (preferably not in Spain and Italy yet, but such options can be considered).\n"
                "\n"
                "## Reasoning: The job description specifies that the location should be \"except for Portugal,\" indicating that candidates from Portugal are not being considered for this role. While it mentions a preference against candidates from Spain and Italy, it also states that such options can still be considered. Therefore, the primary restriction is on candidates located in Portugal. The description does not impose strict restrictions on Spain and Italy, implying flexibility. Thus, the location should be summarized with the specific exclusion mentioned.\n"
                "## Candidate's Location: NOT Portugal\n"
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

    print(response)

    # Parse the response from the LLM
    extracted_data = parse_llm_vacancy_location_response(response, add_tokens_info=add_tokens_info)

    return extracted_data
