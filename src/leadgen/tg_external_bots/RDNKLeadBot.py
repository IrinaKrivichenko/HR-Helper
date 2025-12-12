import re

def find_lead_pattern(text: str):
    # Regular expression "Lead X of Y"
    pattern = r'Lead \d+ of \d+'
    matches = re.findall(pattern, text)
    return matches


def parse_lead_text(text):
    # Regular expressions for data extraction
    patterns = {
        "Company Name": r"Company:\s*(.+?)\n",
        "Company Website": r"• Domain:\s*(.+?)\n",
        "Company location / relevant office": r"• Company location / relevant office:\s*(.+?)\n",
        "Title": r"• Person:\s*(.+?)\n",
        "LinkedIn Profile": r"• LinkedIn:\s*(http[s]?://[^\s]+)",
        "Signals": r"• Signals:\s*(.*?)(?=\n• Why Relevant Now:|\Z)",
        "Why Relevant Now": r"• Why Relevant Now:\s*([^\n]+)",
        "Suggested Outreach": r"•\s*Suggested Outreach:\s*\n\s*([^\n]+)",
    }

    result = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            if key == "LinkedIn Profile":
                result[key] = match.group(1).strip() if match.group(1) else ""
            else:
                result[key] = match.group(1).strip()
        else:
            result[key] = ""

    domain = result["Company Website"]
    if not domain.startswith(("http://", "https://")):
        result["Company Website"] = f"http://{domain}"

    # Clearing data from unnecessary characters
    for key in result:
        if isinstance(result[key], str):
            result[key] = result[key].replace("•", "").strip()

    return result
