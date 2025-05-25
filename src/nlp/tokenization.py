import re
from nltk import word_tokenize
from nltk.data import path as nltk_path
nltk_path.append("src/nlp/nltk_data")

def get_tokens(text):
    tokens = word_tokenize(text.lower())
    english_letter_pattern = re.compile(r'[a-zA-Z]')
    filtered_tokens = [token for token in tokens if english_letter_pattern.search(token)]
    return set(filtered_tokens)
