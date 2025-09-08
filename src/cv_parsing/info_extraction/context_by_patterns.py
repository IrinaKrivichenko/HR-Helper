import re
from typing import List

def extract_context_by_patterns(
    cv_text: str,
    patterns: List[str],
    lines_around: int = 1
) -> str:
    """
    Extracts lines from CV text that match any of the given regex patterns,
    along with the specified number of lines before and after each match.
    Returns a single joined string with relevant context.
    """
    lines = cv_text.split('\n')
    relevant_lines = set()
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    for i, line in enumerate(lines):
        for pattern in compiled_patterns:
            if pattern.search(line):
                start = max(0, i - lines_around)
                end = min(len(lines), i + lines_around + 1)
                relevant_lines.update(lines[start:end])

    return "\n\n".join(relevant_lines)
