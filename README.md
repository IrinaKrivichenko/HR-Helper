# Telegram Bot for Candidate Matching

A Telegram bot designed to match candidates to job descriptions, interact with Google Sheets, Google Drive, and LinkedIn, and perform NLP analysis on resumes.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features

- Match candidates to job descriptions.
- Read and write data to Google Sheets.
- Interact with Google Drive and LinkedIn.
- Perform NLP analysis on resumes using NLTK and OpenAI models.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/telegram-bot.git
   cd telegram-bot
   ```
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables and configuration files in the /configs directory. Configure your API keys and settings in the /configs directory. Ensure you have the necessary permissions and access tokens for Google Sheets, Google Drive, LinkedIn, and OpenAI.

## Usage
1. Run the bot:

   ```bash
   python main.py
   ```
2. Interact with the bot through Telegram to match candidates, analyze resumes, and more.

## Testing
Run the tests to ensure everything is working correctly:

   ```bash
   python -m unittest discover -s tests
   ```