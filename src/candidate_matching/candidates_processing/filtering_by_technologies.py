from src.logger import logger
from src.data_processing.nlp.tokenization import get_tokens
import os
from dotenv import load_dotenv
load_dotenv()


def mitigate_cloud_technologies_impact(tech_string):
    # Define the cloud platforms and their short forms
    aws_full = "Amazon Web Services (AWS)"
    azure_full = "Microsoft Azure (Azure)"
    gcp_full = "Google Cloud Platform (GCP)"

    aws_short = "AWS"
    azure_short = "Azure"
    gcp_short = "GCP"

    # Process the string according to the specified rules
    if aws_full in tech_string:
        tech_string = tech_string.replace(aws_full, aws_short)
        tech_string = tech_string.replace(azure_full, "").replace(gcp_full, "")
    elif azure_full in tech_string:
        tech_string = tech_string.replace(azure_full, azure_short)
        tech_string = tech_string.replace(gcp_full, "")
    elif gcp_full in tech_string:
        tech_string = tech_string.replace(gcp_full, gcp_short)

    # Remove any leading or trailing commas and extra whitespace
    tech_string = ', '.join(filter(None, (item.strip() for item in tech_string.split(',') if item.strip())))

    return tech_string

def filter_technologies_by_vacancy_tokens(candidate_stack: str, vacancy_tokens: set) -> str:
    # Split the candidate stack into individual technologies
    technologies = [tech.strip() for tech in candidate_stack.split(',')]
    # Retain only those technologies in which at least one token from the vacancy was found
    filtered_techs = [
        tech for tech in technologies
        if any(token.lower() in tech.lower() for token in vacancy_tokens)
    ]
    return ', '.join(filtered_techs)

def calculate_tech_coverage(candidate_stack: str, vacancy_technologies_list: list) -> str:
    candidate_techs = [tech.strip() for tech in candidate_stack.split(',') if tech.strip()]
    candidate_count = len(candidate_techs)
    vacancy_count = len(vacancy_technologies_list)
    return f"{candidate_count}/{vacancy_count}"

def covered_percentage(vacancy_set: set, candidate_set: set) -> float:
    """
    Calculates the percentage of coverage of the vacancy requirements by a given candidate.
    """
    if not vacancy_set:
        return 0.0  # Avoid division by zero
    intersection = vacancy_set & candidate_set  # Find common elements
    return (len(intersection) / len(vacancy_set)) * 100  # Calculate percentage

def get_names(df):
    names_string = ', '.join(df['Full Name'].astype(str))
    if 'Coverage' in df.columns:
        min_coverage = df['Coverage'].min()
        max_coverage = df['Coverage'].max()
        names_string = f"{names_string}\nCoverage: {min_coverage}-{max_coverage}\n"
    return names_string


def filter_by_technologies(vacancy_info, df):
    """
    Filters candidates based on programming languages and technologies mentioned in the vacancy information.

    Args:
    - vacancy_info (dict): The vacancy description.
    - df (pd.DataFrame): DataFrame containing candidate data.

    Returns:
    - tuple: Filtered DataFrame and coverage percentage.
    """
    MIN_CANDIDATES_THRESHOLD = int(os.getenv("MIN_CANDIDATES_THRESHOLD"))
    coverage_percentage = "0%"
    vacancy_programming_languages = vacancy_info.get("Extracted Programming Languages", "")
    vacancy_technologies = vacancy_info.get("Extracted Technologies", "")
    vacancy_technologies = mitigate_cloud_technologies_impact(vacancy_technologies)
    vacancy_technologies_set = get_tokens(vacancy_technologies)

    # Step 3: Get candidates with fully covered programming languages
    pl_threshold = 100
    if vacancy_programming_languages and not vacancy_programming_languages.startswith('No'):
        vacancy_programming_set = get_tokens(vacancy_programming_languages)
        df['Coverage'] = df['Stack'].apply(
            lambda x: covered_percentage(vacancy_programming_set, get_tokens(x))
        )
        full_pl_coverage_df = df[df['Coverage'] == pl_threshold]
        logger.info(f"Number of candidates with full programming languages coverage: {len(full_pl_coverage_df)}\n{get_names(full_pl_coverage_df)}\n{vacancy_programming_languages}")

        if len(full_pl_coverage_df) < MIN_CANDIDATES_THRESHOLD: # full_pl_coverage_df.empty:
            pl_threshold = 60
            partial_pl_coverage_df = df[df['Coverage'] >= pl_threshold]
            logger.info(f"Number of candidates with partial programming languages coverage (>= {pl_threshold}%): {len(partial_pl_coverage_df)}\n{get_names(partial_pl_coverage_df)}\n{vacancy_programming_languages}")
            coverage_percentage = f"programming languages coverage >= {pl_threshold}%"
        else:
            partial_pl_coverage_df = full_pl_coverage_df
            coverage_percentage = f"full programming languages coverage"
    else:
        partial_pl_coverage_df = df
        vacancy_programming_set = set()
        logger.info("No programming languages specified in vacancy.")

    # Step 5: Get candidates with coverage of other technologies
    tech_threshold = 30
    if vacancy_technologies and not vacancy_technologies.startswith('No'):
        vacancy_technologies_set = get_tokens(vacancy_technologies)
        partial_pl_coverage_df['Coverage'] = partial_pl_coverage_df['Stack'].apply(
            lambda x: covered_percentage(vacancy_technologies_set, get_tokens(x))
        )
        full_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Coverage'] >= tech_threshold]
        logger.info(f"Number of candidates with full technologies coverage (>= {tech_threshold}%): {len(full_tech_coverage_df)}\n{get_names(full_tech_coverage_df)}\n{vacancy_technologies}")

        if len(full_tech_coverage_df) < MIN_CANDIDATES_THRESHOLD:  #full_tech_coverage_df.empty:
            tech_threshold = 20
            partial_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Coverage'] >= tech_threshold]
            logger.info(f"Number of candidates with partial technologies coverage (>= {tech_threshold}%): {len(partial_tech_coverage_df)}\n{get_names(partial_tech_coverage_df)}\n{vacancy_technologies}")
            if len(partial_tech_coverage_df) < MIN_CANDIDATES_THRESHOLD: #partial_tech_coverage_df.empty:
                tech_threshold = 10
                partial_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Coverage'] >= tech_threshold]
                logger.info(f"Number of candidates with partial technologies coverage (>= {tech_threshold}%): {len(partial_tech_coverage_df)}\n{get_names(partial_tech_coverage_df)}\n{vacancy_technologies}")
        else:
            partial_tech_coverage_df = full_tech_coverage_df
        coverage_percentage = f"{coverage_percentage}\nother technologies coverage (>= {tech_threshold}%"
    else:
        partial_tech_coverage_df = partial_pl_coverage_df
        vacancy_technologies_set = set()
        logger.info("No technologies specified in vacancy.")

    all_vacancy_tokens_set = vacancy_programming_set.union(vacancy_technologies_set)
    partial_tech_coverage_df['Stack'] = partial_tech_coverage_df['Stack'].apply(lambda stack: filter_technologies_by_vacancy_tokens(stack, all_vacancy_tokens_set))
    all_vacancy_technologies = f"{vacancy_programming_languages}\n{vacancy_technologies}"
    all_vacancy_technologies_list = [tech.strip() for tech in all_vacancy_technologies.split('\n') if tech.strip()]
    partial_tech_coverage_df['Tech Coverage'] = partial_tech_coverage_df['Stack'].apply(lambda stack: calculate_tech_coverage(stack, all_vacancy_technologies_list))

    return partial_tech_coverage_df, coverage_percentage

