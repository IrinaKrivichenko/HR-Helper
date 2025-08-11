
import pandas as pd
import re

def filter_candidates_by_location(df, location_requirements):
    # List of European Union countries
    eu_countries = {
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden'
    }

    # Function to remove emoji flags from location strings
    def remove_emoji_flags(location):
        # Regular expression to match emoji flags
        emoji_pattern = re.compile("["
            u"\U0001F1E0-\U0001F1FF"  # Flags
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', location).strip()

    # If location requirements are "Any location", return original DataFrame
    if "Any location" in location_requirements:
        return df

    # Create a temporary column with locations without emoji flags
    df['Clean Location'] = df['Location'].apply(lambda x: [remove_emoji_flags(loc.strip()) for loc in x.split(',')])

    # Splitting location requirements by commas
    location_list = [loc.strip() for loc in location_requirements.split(',')]

    # Check if "European Union" is in the requirements
    if "European Union" in location_list:
        # Filter candidates whose countries are in the list of EU countries
        df = df[df['Clean Location'].apply(lambda x: any(loc in eu_countries for loc in x))]

    # Determine if the requirements contain countries with the prefix "NOT"
    not_countries = [loc.replace("NOT ", "").strip() for loc in location_list if loc.startswith("NOT ")]
    allowed_countries = [loc.strip() for loc in location_list if not loc.startswith("NOT ") and loc != "European Union"]

    # If there are countries with the prefix "NOT", exclude rows where all locations are in not_countries
    if not_countries:
        df = df[df['Clean Location'].apply(lambda x: any(loc not in not_countries for loc in x))]

    # If there are allowed countries, leave only rows where at least one location is in allowed_countries
    if allowed_countries:
        # Only apply allowed countries filter if European Union is not specified
        if "European Union" not in location_list:
            df = df[df['Clean Location'].apply(lambda x: any(loc in allowed_countries for loc in x))]

    # Drop the temporary column
    df.drop(columns=['Clean Location'], inplace=True)
    return df