import pandas as pd

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
    # print(diff)
    return len(intersection) / len(union) if union != 0 else 0


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
