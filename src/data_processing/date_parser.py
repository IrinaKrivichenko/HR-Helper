import re
from datetime import date

import pandas as pd

# Finds the first substring of the form YYYY-MM-DD in a string
DATE_RE = re.compile(r'(\d{4})-(\d{2})-(\d{2})')

def parse_date_only(s: str) -> date:
    m = DATE_RE.search(s)
    if not m:
        raise ValueError("Не найдена дата в формате YYYY-MM-DD")
    y, mth, d = map(int, m.groups())
    return date(y, mth, d)

def days_since(s: str, current_date: date | None = None) -> int:
    """
    Returns the number of calendar days from the dates in the string to "today."
    Ignores any extra characters (including the day of the week).
    If no date in YYYY-MM-DD is found, returns 1000.
    """
    try:
        d = parse_date_only(s)
    except ValueError:
        return 1000
    current_date = current_date or date.today()
    return (current_date - d).days


def is_available_soon(
                            value: str | pd.Series,
                            column_name: str | None = None,
                            days_threshold: int = 30,
                            today: date | None = None
                        ) -> bool:
    """
    Checks if a date in the value is relevant:
    - If empty, NaN, or blank → True.
    - If days until date ≤ days_threshold → True.
    - Otherwise → False.

    :param value: Cell value (str) or DataFrame row (pd.Series).
    :param column_name: Column name if value is a DataFrame row.
    :param days_threshold: Day threshold (default: 30).
    :param today: Current date (default: today).
    :return: bool
    """
    today = today or date.today()

    if isinstance(value, pd.Series):
        if column_name is None:
            raise ValueError("Specify column_name for pd.Series")
        value = value.get(column_name, '')

    if pd.isna(value) or value == '':
        return True

    days_left = days_since(value, today)
    return days_left <= days_threshold

