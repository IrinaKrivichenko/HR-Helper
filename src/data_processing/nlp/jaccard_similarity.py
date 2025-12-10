from typing import List, Tuple

import pandas as pd

from src.data_processing.nlp.tokenization import get_tokens


def calculate_jaccard_similarity(set1, set2):
    """
    Calculate the Jaccard similarity coefficient between two sets.

    Args:
    - set1 (set): The first set of words.
    - set2 (set): The second set of words.

    Returns:
    - float: The Jaccard similarity coefficient.
    """
    # Convert to sets if they are not already
    if not isinstance(set1, set):
        set1 = set(set1)
    if not isinstance(set2, set):
        set2 = set(set2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    diff = union-intersection
    #  logger.info(diff)
    return len(intersection) / len(union) if union else 0


def find_most_similar_row(column: pd.Series, target_string: str,
                          initial_threshold: float = 0.9, step: float = 0.1) -> str:
    """
    Finds the most similar row in a DataFrame column to a given string using Jaccard similarity.
    Args:
    - column (pd.Series): The DataFrame column to search in.
    - target_string (str): The target string to compare against.
    - initial_threshold (float): The initial threshold for Jaccard similarity.
    - step (float): The step to decrease the threshold by in each iteration.
    Returns:
    - str: The most similar row found, or None if no match is found.
    """
    target_set = set(target_string)
    # Start with the initial threshold and decrease it gradually
    threshold = initial_threshold
    while threshold >= 0:
        for index, value in column.items():
            value_set = set(value)
            similarity = calculate_jaccard_similarity(target_set, value_set)
            if similarity >= threshold:
                return index, value
        threshold -= step
    return None

def find_similar_lines(
    lines: List[str],
    target_string: str,
    initial_threshold: float = 0.7,
    step: float = 0.1,
    min_threshold: float = 0.3
) -> List[Tuple[int, float]]:
    """
    Finds all lines similar to the target string using Jaccard similarity over token sets.

    Args:
        lines: List of lines to search in.
        target_string: The target string to compare against.
        initial_threshold: The initial threshold for Jaccard similarity.
        step: The step to decrease the threshold by in each iteration.
        min_threshold: The minimum threshold for Jaccard similarity.

    Returns:
        List[Tuple[int, float]]: List of tuples (index, similarity) for all lines that exceed
        the threshold on the first threshold level that yields matches. Sorted by index asc.
    """
    # Tokenize target into a set of tokens (English letters only by your tokenizer)
    target_tokens = get_tokens(target_string or "")

    # Pre-tokenize all lines and compute similarities once
    scored: List[Tuple[int, float]] = []
    for i, line in enumerate(lines):
        s = "" if line is None else str(line)
        line_tokens = get_tokens(s) if s else set()
        sim = calculate_jaccard_similarity(target_tokens, line_tokens)
        scored.append((i, sim))

    # Decrease threshold until matches appear or we hit min_threshold
    threshold = float(initial_threshold)
    while threshold >= min_threshold:
        hits = [(i, sim) for (i, sim) in scored if sim >= threshold]
        if hits:
            hits.sort(key=lambda x: x[0])  # keep top-to-bottom order in resume
            return hits
        threshold = round(threshold - step, 10)  # mitigate float precision drift

    return []

