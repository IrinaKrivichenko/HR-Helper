import re

from src.data_processing.nlp.llm_handler import extract_and_parse_token_section


def split_vacancies(text, llm_handler, model="gpt-4o-mini"):
    """
    Splits the given text into separate vacancy descriptions using LLMHandler.

    Args:
    - text (str): The text containing multiple vacancy descriptions.
    - llm_handler: Handler for interacting with the language model.

    Returns:
    - list: A list of strings, each representing a separate vacancy description.
    """
    # Define the prompt for the language model
    prompt = [
        {"role": "system", "content": "You are an expert text processor specializing in analyzing and structuring job descriptions."},
        {"role": "user", "content": (
            f"Divide the text into separate vacancies. Each vacancy should be highlighted as a separate block with the heading \"# Vacancy X\", where X is the vacancy number. Keep the original text of each vacancy unchanged.\n\n"
            f"For texts where individual vacancy descriptions are followed by common information for all vacancies, append the common information to each vacancy.\n\n"
            f"# Example1 text:\n"
            f"Фаза 1: Доказ канцэпцыі (PoC)\nМэта: Праверыць будаўніцтва базавай функцыянальнасці бота за кароткі час (да 2 месяцаў) і прадэманстраваць кліенту.  \nТэрмін: 7-11 дзён.\nасноўныя задачы:\n0  \nЗафіксаваць спіс падатковых дакументаў (пасля, Падаткавы кодэкс РБ асноўная частка і дадатковая частка), па якіх будзе працаваць бот.  \n1  \nСтварэнне базывага Telegram-бота:  \nСтварэнне бота праз BotFather і атрыманне токена API.  \nНаладка базавай сувязі паміж ботам і серверным кодам.  \n2  \nРэалізацыя функцыянальнасці (LLM+RAG):  \nБот трэцім простым пытанням ад спажыўцоў.  \n3  \nДэманстрацыя вынікаў:  \nПрататып бота для тэставання кліентам.\n \nАд нас патрэбна тольки частка AI/ML.\nСтарэйшы распрацоўшчык Full Stack Prompt Engineering (6 гадоў пацверджанага вопыту)  \nПатрабаванні:\n  Не менш за 6 гадоў вопыту распрацоўкі Full Stack  \nПацверджаны вопыт працы з Prompt Engineering і інтэграванымі з штучным інтэлектам працоўнымі працэсамі распрацоўкі  \nГлыбокае разуменне архітэктуры бэкенда і фронтенда  \nАнглійская мова: B2+\n  Удзел: 3-4 месяцы (5-6 гадзін у дзень)  \nМесцазнаходжанне: не патрабуецца  \nПраект: воблачная SaaS-платформа  \nпачатак: канец мая\n"
            f"# Result Example1:\n"
            f"## Vacancy 1\nФаза 1: Доказ канцэпцыі (PoC)\nМэта: Праверыць будаўніцтва базавай функцыянальнасці бота за кароткі час (да 2 месяцаў) і прадэманстраваць кліенту.  \nТэрмін: 7-11 дзён.\nасноўныя задачы:\n0  \nЗафіксаваць спіс падатковых дакументаў (пасля, Падаткавы кодэкс РБ асноўная частка і дадатковая частка), па якіх будзе працаваць бот.  \n1  \nСтварэнне базывага Telegram-бота:  \nСтварэнне бота праз BotFather і атрыманне токена API.  \nНаладка базавай сувязі паміж ботам і серверным кодам.  \n2  \nРэалізацыя функцыянальнасці (LLM+RAG):  \nБот трэцім простым пытанням ад спажыўцоў.  \n3  \nДэманстрацыя вынікаў:  \nПрататып бота для тэставання кліентам.\n \nАд нас патрэбна тольки частка AI/ML.\n## Vacancy 2\nСтарэйшы распрацоўшчык Full Stack Prompt Engineering (6 гадоў пацверджанага вопыту)  \nПатрабаванні:\n  Не менш за 6 гадоў вопыту распрацоўкі Full Stack  \nПацверджаны вопыт працы з Prompt Engineering і інтэграванымі з штучным інтэлектам працоўнымі працэсамі распрацоўкі  \nГлыбокае разуменне архітэктуры бэкенда і фронтенда  \nАнглійская мова: B2+\n  Удзел: 3-4 месяцы (5-6 гадзін у дзень)  \nМесцазнаходжанне: не патрабуецца  \nПраект: воблачная SaaS-платформа  \nпачатак: канец мая\n"
            f"# Example2 text:\n"
            f"Data Engineer\nУровень: Senior Principal\nStack: AWS, Python, SQL\n\nData Analyst\nУровень: Middle+\nStack: Excel, Tableau, Snowflake, SQL\n\nPython\nУровень: Middle+/Senior\nОпыт: DE\n\nFullstack (Python 70%, React 30%)\nУровень: Senior\n\nPython\nУровень: Senior\nStack: FastAPI, SQL\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"# Result Example2:\n"
            f"## Vacancy 1\nData Engineer\nУровень: Senior Principal\nStack: AWS, Python, SQL\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"## Vacancy 2\nData Analyst\nУровень: Middle+\nStack: Excel, Tableau, Snowflake, SQL\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"## Vacancy 3\nPython\nУровень: Middle+/Senior\nОпыт: DE\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"## Vacancy 4\nFullstack (Python 70%, React 30%)\nУровень: Senior\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"## Vacancy 5\nPython\nУровень: Senior\nStack: FastAPI, SQL\n\nEnglish level: от B2+\n\nДлительность: от 12 мес.\nЛокация: только Польша (частичное трудоустройство кандидата к нам по UoP или по b2b)\nКонтакты: @ElenaChizhikovaa, @polina137"
            f"Now process the following text:\n{text}\n\n"
            f"Result:"
        )}
    ]
    # Get the response from the language model
    approximate_tokens = len(text) + 100
    response = llm_handler.get_answer(prompt, model=model, max_tokens=approximate_tokens)
    response, _ = extract_and_parse_token_section(response=response)

    # Use regular expressions to split the response into separate vacancies
    vacancies = re.split(r'## Vacancy \d+', response)
    vacancies = [vacancy.strip() for vacancy in vacancies if vacancy.strip()]


    return vacancies


