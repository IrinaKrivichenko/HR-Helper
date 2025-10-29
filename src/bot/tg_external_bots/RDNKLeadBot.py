import re

def find_lead_pattern(text: str):
    # Regular expression "Lead X of Y"
    pattern = r'Lead \d+ of \d+'
    matches = re.findall(pattern, text)
    return matches


def parse_lead_text(text):
    # Regular expressions for data extraction
    patterns = {
        "Company": r"Company:\s*(.+?)\n",
        "Domain": r"• Domain:\s*(.+?)\n",
        "Company location / relevant office": r"• Company location / relevant office:\s*(.+?)\n",
        "Person: Company": r"• Person:\s*(.+?)\n",
        "LinkedIn": r"• LinkedIn:\s*(http[s]?://[^\s]+)",
        "Signals": r"• Signals:\s*(.*?)(?=\n• Why Relevant Now:|\Z)",
        "Why Relevant Now": r"• Why Relevant Now:\s*([^\n]+)",
        "Suggested Outreach": r"•\s*Suggested Outreach:\s*\n\s*([^\n]+)",
    }

    result = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            if key == "LinkedIn":
                result[key] = match.group(1).strip() if match.group(1) else ""
            else:
                result[key] = match.group(1).strip()
        else:
            result[key] = ""

    domain = result["Domain"]
    if not domain.startswith(("http://", "https://")):
        result["Domain"] = f"http://{domain}"

    # Clearing data from unnecessary characters
    for key in result:
        if isinstance(result[key], str):
            result[key] = result[key].replace("•", "").strip()

    return result
