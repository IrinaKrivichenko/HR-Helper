from typing import List, Dict, Set, Tuple, Callable

def create_normalizing_dict(
    values: List[str],
    normalize_func: Callable[[str], str] = lambda x: x.lower().strip()
) -> Dict[str, str]:
    """
    Converts a list of values into a dictionary with normalized keys.

    Args:
    values: List of values (e.g., ["Python Developer", "Finance"]).
    normalize_func: Function for normalization (default: convert to lowercase and trim spaces).

    Returns:
    A dictionary where the keys are the normalized values and the values are the original ones.
    """
    value_dict = {}
    for value in values:
        normalized_value = normalize_func(value)
        value_dict[normalized_value] = value
    return value_dict

def match_values(
    allowed_values: List[str],
    input_values: List[str],
    normalize_func: Callable[[str], str] = lambda x: x.lower().strip()
) -> Tuple[Set[str], Set[str]]:
    """
    Matches values against an allowed list.
    Args:
    allowed_values: Allowed list of values (e.g., ["Python Developer", "Finance"]).
    input_values: List of values to check (e.g., ["python developer", "E-commerce"]).
    normalize_func: Function for normalizing values.
    Returns:
    Two sets: (existing values, new values).
    """
    value_dict = create_normalizing_dict(allowed_values, normalize_func)

    matches_set = set()
    proposed_set = set()

    for value in input_values:
        normalized_value = normalize_func(value)
        if normalized_value in value_dict:
            matches_set.add(value_dict[normalized_value])
        else:
            proposed_set.add(value)

    return matches_set, proposed_set
