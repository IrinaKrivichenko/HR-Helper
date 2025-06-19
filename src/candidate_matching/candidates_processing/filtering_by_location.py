import pandas as pd

def filter_candidates_by_location(df, location_requirements):
    # List of European Union countries
    eu_countries = {
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden'
    }

    # If location requirements are "Any location", return original DataFrame
    if location_requirements.strip().lower() == "any location":
        return df

    # Splitting location requirements by commas
    location_list = [loc.strip() for loc in location_requirements.split(',')]

    # Check if "European Union" is in the requirements
    if "European Union" in location_requirements:
        # Filter candidates whose countries are in the list of EU countries
        df = df[df['Location'].isin(eu_countries)]
    else:
        # Determine if the requirements contain countries with the prefix "NOT"
        not_countries = [loc.replace("NOT ", "").strip() for loc in location_list if loc.startswith("NOT ")]
        allowed_countries = [loc.strip() for loc in location_list if not loc.startswith("NOT ") and loc != "European Union"]

        # If there are countries with the prefix "NOT",
        if not_countries:
            df = df[~df['Location'].isin(not_countries)]

        # If there are allowed countries, leave only their
        if allowed_countries:
            df = df[df['Location'].isin(allowed_countries)]

    return df


