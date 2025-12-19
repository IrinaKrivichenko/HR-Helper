import re
from datetime import date

# Finds the first substring of the form YYYY-MM-DD in a string
DATE_RE = re.compile(r'(\d{4})-(\d{2})-(\d{2})')

def parse_date_only(s: str) -> date:
    m = DATE_RE.search(s)
    if not m:
        raise ValueError("Не найдена дата в формате YYYY-MM-DD")
    y, mth, d = map(int, m.groups())
    return date(y, mth, d)

def days_since(s: str, today: date | None = None) -> int:
    """
    Returns the number of calendar days from the dates in the string to "today."
    Ignores any extra characters (including the day of the week).
    If no date in YYYY-MM-DD is found, returns 1000.
    """
    try:
        d = parse_date_only(s)
    except ValueError:
        return 1000
    today = today or date.today()
    return (today - d).days
