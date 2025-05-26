
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

from src.bot.bot import application

if __name__ == "__main__":
    application.run_polling()


#
# /project_root
# │
# ├── /configs
# │   ├── config.py          # Конфигурационные параметры, API ключи и т.д.
# │   └── settings.ini       # Дополнительные настройки
# │
# ├── /src
# │   ├── /bot
# │   │   ├── bot.py         # Основной код бота
# │   │   ├── classifier.py    # Обработчики команд и сообщений
# │   │   └── utils.py       # Вспомогательные функции для бота
# │   │
# │   ├── /google_services
# │   │   ├── sheets.py      # Работа с Google Таблицами
# │   │   ├── drive.py       # Работа с Google Диском
# │   │   └── utils.py       # Вспомогательные функции для Google сервисов
# │   │
# │   ├── /linkedin
# │   │   └── api.py         # Работа с LinkedIn API
# │   │
# │   ├── /nlp
# │   │   ├── /nltk_data     # Данные для NLTK
# │   │   ├── embedding_handler.py      # эмбеддинговые модели от OpenAI
# │   │   ├── llm_handler.py # Языковые модели от OpenAI
# │   │   ├── tokenizer.py   # Токенизация с использованием NLTK
# │   │   └── utils.py       # Вспомогательные функции для NLP
# │   │
# │   ├── /candidate_matching
# │   │   ├── matcher.py     # Логика подбора кандидатов
# │   │   ├── vacancy_splitter.py     #
# │   │   └── utils.py       # Вспомогательные функции для подбора кандидатов
# │   │
# │   ├── /resume_analysis
# │   │   ├── parser.py      # Анализ резюме кандидатов
# │   │   └── utils.py       # Вспомогательные функции для анализа резюме
# │   │
# │   └── /market_analysis
# │       ├── analyzer.py    # Анализ вакансий с точки зрения потребностей рынка
# │       └── utils.py       # Вспомогательные функции для анализа рынка
# │
# ├── /tests
# │   ├── test_bot.py        # Тесты для бота
# │   ├── test_google_services.py # Тесты для Google сервисов
# │   ├── test_nlp.py        # Тесты для NLP функций
# │   ├── test_candidate_matching.py # Тесты для подбора кандидатов
# │   ├── test_resume_analysis.py # Тесты для анализа резюме
# │   └── test_market_analysis.py # Тесты для анализа рынка
# │
# ├── /data
# │   ├── /raw               # Исходные данные
# │   ├── /processed         # Обработанные данные
# │   └── /models            # Модели и токенизаторы
# │
# ├── /docs
# │   └── documentation.md   # Документация проекта
# │
# ├── main.py                # Точка входа в приложение
# ├── requirements.txt       # Зависимости проекта
# └── README.md              # Описание проекта