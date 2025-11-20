import re

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols and icons
    "\U0001F680-\U0001F6FF"  # Transport and signs
    "\U0001F1E0-\U0001F1FF"  # Country flags
    "\U00002500-\U00002BEF"  # Symbols and geometric shapes
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Additional symbols
    "\U0001f926-\U0001f937"  # Emotions and gestures
    "\U0001F100-\U0001FFFF"  # Additional symbols and flags
    "\U00010000-\U0010ffff"  # Symbols from additional Unicode planes
    "\u2640-\u2642"         # Gender symbols
    "\u2600-\u2B55"         # Miscellaneous symbols
    "\u200d"               # Zero-width joiner
    "\u23cf"               # Eject symbol
    "\u23e9"               # Fast-down button
    "\u231a"               # Watch
    "\ufe0f"               # Variation selector
    "\u3030"               # Wavy dash
    "]+",
    flags=re.UNICODE,
)

def extract_emoji(text):
    """
        Extracts all emojis from a string and returns them as a single string.
        Args:
            text (str): Input string that may contain emojis.
        Returns:
            str: String containing only emojis, or None if no emojis found.
        """
    emojis = EMOJI_PATTERN.findall(text)
    return ''.join(emojis) if emojis else None



def remove_emojis(text: str) -> str:
    """
    Removes all emojis from a string, leaving only regular characters.
    Args:
        text (str): Input string that may contain emojis.
    Returns:
        str: String without emojis.
    """
    return EMOJI_PATTERN.sub("", text).strip()


