
import pandas as pd

from src.candidate_matching.candidates_processing.filtering_by_location import filter_candidates_by_location
from src.data_processing.vector_utils import cosine_similarity
from src.nlp.embedding_handler import add_embeddings_column
from src.logger import logger

import os
from dotenv import load_dotenv

from src.nlp.tokenization import get_tokens

load_dotenv()


def filter_candidates_by_seniority(df, required_seniority):
    # Determine the order of seniority levels
    seniority_order = ['Junior', 'Middle', 'Senior', 'Principal']

    # If 'Any' is specified, return the original DataFrame
    if required_seniority not in seniority_order:
        return df

    # Determine the range of seniority levels to filter on
    if required_seniority == 'Junior':
        # For Junior, select Junior and Middle
        allowed_seniorities = seniority_order[:2]
    elif required_seniority == 'Middle':
        # For Middle, select Junior, Middle, and Senior
        allowed_seniorities = seniority_order[:3]
    elif required_seniority == 'Senior':
        # For Senior, select Middle, Senior, and Principal
        allowed_seniorities = seniority_order[1:]
    elif required_seniority == 'Principal':
        # For Principal, select Senior and Principal
        allowed_seniorities = seniority_order[2:]

    # Filter candidates by seniority levels
    filtered_df = df[df['Seniority'].isin(allowed_seniorities)]

    return filtered_df

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


def covered_percentage(vacancy_set: set, candidate_set: set) -> float:
    """
    Calculates the percentage of coverage of the vacancy requirements by a given candidate.
    """
    if not vacancy_set:
        return 0.0  # Avoid division by zero

    intersection = vacancy_set & candidate_set  # Find common elements
    return (len(intersection) / len(vacancy_set)) * 100  # Calculate percentage

def primary_filtering_by_vacancy(vacancy_info, df):
    """
    Filters candidates based on the given vacancy information.

    Args:
    - vacancy_info (dict): The vacancy description.
    - df (pd.DataFrame): DataFrame containing candidate data.

    Returns:
    - pd.DataFrame: Filtered DataFrame with candidates meeting the criteria.
    """

    # Step 1: Filter by location
    location_filtered_df = filter_candidates_by_location(df, vacancy_info.get("Extracted Location", "Any location"))
    logger.info(f"Number of candidates after location filtering: {len(location_filtered_df)}")

    # Step 2: Filter by seniority
    seniority_filtered_df = filter_candidates_by_seniority(location_filtered_df, vacancy_info.get("Extracted Seniority", "Any"))
    logger.info(f"Number of candidates after seniority filtering: {len(seniority_filtered_df)}")

    coverage_percentage = "0%"
    # Step 3: Get candidates with fully covered programming languages
    vacancy_programming_languages = vacancy_info.get("Extracted Programming Languages", "")
    pl_threshold = 100
    if vacancy_programming_languages:
        vacancy_programming_set = set(vacancy_programming_languages.split('\n'))
        seniority_filtered_df['Programming Languages Coverage'] = seniority_filtered_df['Stack'].apply(
            lambda x: covered_percentage(vacancy_programming_set, get_tokens(x))
        )
        full_pl_coverage_df = seniority_filtered_df[seniority_filtered_df['Programming Languages Coverage'] == pl_threshold]
        logger.info(f"Number of candidates with full programming languages coverage: {len(full_pl_coverage_df)}")

        # Step 4: If the list from step 3 is empty, get candidates with 60% or more coverage
        if full_pl_coverage_df.empty:
            pl_threshold = 60
            partial_pl_coverage_df = seniority_filtered_df[seniority_filtered_df['Programming Languages Coverage'] >= pl_threshold]
            logger.info(f"Number of candidates with partial programming languages coverage (>= {pl_threshold}%): {len(partial_pl_coverage_df)}")
            coverage_percentage = f"programming languages coverage >= {pl_threshold}%"
        else:
            partial_pl_coverage_df = full_pl_coverage_df
            coverage_percentage = f"full programming languages coverage"
    else:
        partial_pl_coverage_df = seniority_filtered_df
        logger.info("No programming languages specified in vacancy.")

    # Step 5: Get candidates with 60% or more coverage of other technologies
    tech_threshold = 60
    vacancy_technologies = vacancy_info.get("Extracted Technologies", "")
    if vacancy_technologies:
        vacancy_technologies = mitigate_cloud_technologies_impact(vacancy_technologies)
        vacancy_technologies_set = set(vacancy_technologies.split('\n'))
        partial_pl_coverage_df['Technologies Coverage'] = partial_pl_coverage_df['Stack'].apply(
            lambda x: covered_percentage(vacancy_technologies_set, get_tokens(x))
        )
        full_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Technologies Coverage'] >= tech_threshold]
        logger.info(f"Number of candidates with full technologies coverage (>= {tech_threshold}%): {len(full_tech_coverage_df)}")

        # Step 6: If the list from step 5 is empty, get candidates with 30% and more coverage, then 10% and more coverage
        if full_tech_coverage_df.empty:
            tech_threshold = 30
            partial_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Technologies Coverage'] >= tech_threshold]
            logger.info(f"Number of candidates with partial technologies coverage (>= {tech_threshold}%): {len(partial_tech_coverage_df)}")
            if partial_tech_coverage_df.empty:
                tech_threshold = 10
                partial_tech_coverage_df = partial_pl_coverage_df[partial_pl_coverage_df['Technologies Coverage'] >= tech_threshold]
                logger.info(f"Number of candidates with partial technologies coverage (>= {tech_threshold}%): {len(partial_tech_coverage_df)}")

        else:
            partial_tech_coverage_df = full_tech_coverage_df
        coverage_percentage = f"{coverage_percentage}\nother technologies coverage (>= {tech_threshold}%"
    else:
        partial_tech_coverage_df = partial_pl_coverage_df
        logger.info("No technologies specified in vacancy.")

    # Step 7: Final filtered DataFrame
    final_filtered_df = partial_tech_coverage_df
    logger.info(f"Number of technologies after final filtering: {len(final_filtered_df)}")

    return final_filtered_df, coverage_percentage


def filter_candidates_by_embedding(vacancy_info, df, embedding_handler, initial_threshold=0.7, min_threshold=0.39,
                                   min_candidates=int(os.getenv("MIN_CANDIDATES_THRESHOLD"))):
    """
    Filters candidates based on embedding similarity with the vacancy description.

    Args:
    - vacancy_info (dict): The vacancy description.
    - df (pd.DataFrame): DataFrame containing candidate data with an 'Embedding' column.
    - embedding_handler: Handler for generating text embeddings.

    Returns:
    - pd.DataFrame: Filtered DataFrame with candidates meeting the similarity threshold.
    - float: The used similarity threshold.
    """
    # Compute the embedding for the vacancy
    # vacancy_embedding = np.array(embedding_handler.get_text_embedding(vacancy)).reshape(1, -1)
    # vacancy_embedding = embedding_handler.get_text_embedding(vacancy)
    vacancy_as_df = pd.DataFrame({
        "Role": [vacancy_info.get("Extracted Role", "")],
        "Stack": [vacancy_info.get("Extracted Technologies", "")],
        "Industry": [vacancy_info.get("Extracted Industry", "")],
        "Expertise": [vacancy_info.get("Extracted Expertise", "")],
        "Location": [vacancy_info.get("Extracted Location", "")]
    })
    vacancy_as_df = add_embeddings_column(vacancy_as_df, write_columns=False)

    # Job description
    vacancy_stack = vacancy_as_df["Stack"][0]
    vacancy_stack = mitigate_cloud_technologies_impact(vacancy_stack)
    vacancy_stack = vacancy_stack.lower()
    # Get a set of job tokens
    vacancy_set = get_tokens(vacancy_stack)
    # Apply the get_tokens() function to all rows in the Stack column and calculate coverage
    df["Coverage"] = df["Stack"].apply(lambda stack: covered_percentage(vacancy_set, get_tokens(stack.lower())))
    # Filter condition with coverage greater than 49%
    stack_coverage_condition = df["Coverage"] > 49
    logger.info(f"number of candidates by stack_coverage_condition {stack_coverage_condition.sum()} ")

    vacancy_embedding = vacancy_as_df['Embedding'][0]

    # if "Extracted Role" in vacancy_info:
    #     filter_by_role = True
    #     vacancy_role_embedding = vacancy_as_df['Role_Embedding'][0]
    # else:
    #     filter_by_role = False
    # if "Extracted Technologies" in vacancy_info:
    #     filter_by_stack = True
    #     vacancy_stack_embedding = vacancy_as_df['Stack_Embedding'][0]
    # else:
    #     filter_by_stack = False

    # Compute similarities with candidate embeddings
    # df['Similarity'] = df['Embedding'].apply(lambda x: cosine_similarity(vacancy_embedding, x)[0][0])
    df['Similarity'] = df['Embedding'].apply(lambda x: cosine_similarity(vacancy_embedding, x))


    # df['Role_Similarity'] = df['Role_Embedding'].apply(lambda x: cosine_similarity(vacancy_role_embedding, np.array(x).reshape(1, -1))[0][0])
    # df['Stack_Similarity'] = df['Stack_Embedding'].apply(lambda x: cosine_similarity(vacancy_stack_embedding, np.array(x).reshape(1, -1))[0][0])

    # exact_candidate_exists = df[df['First Name'] == 'Taisija']
    # if not exact_candidate_exists.empty:
    #     similarity_value = exact_candidate_exists['Similarity'].values[0]
    #     logger.info(f"Similarity for Taisija: {similarity_value}")
    #     similarity_value = exact_candidate_exists['Role_Similarity'].values[0]
    #     logger.info(f"Role_Similarity for Taisija: {similarity_value}")
    #     similarity_value = exact_candidate_exists['Stack_Similarity'].values[0]
    #     logger.info(f"Stack_Similarity for Taisija: {similarity_value}")
    # else:
    #     logger.info("No candidate found with First Name 'Taisija'")

    pd.set_option('display.max_rows', 50)
    # Filter candidates based on the similarity threshold
    consign_similarity_threshold = initial_threshold
    while consign_similarity_threshold >= min_threshold:
        embedding_similarity_condition = df['Similarity'] >= consign_similarity_threshold
        logger.info(f"number of candidates by embedding_similarity_condition{embedding_similarity_condition.sum()} with consign_similarity_threshold {consign_similarity_threshold}")
        filtered_df = df[stack_coverage_condition | embedding_similarity_condition]
        # Check if the number of filtered candidates meets the minimum requirement
        logger.info(f"number of candidates {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        logger.info(filtered_df[["Full Name"]])
        if len(filtered_df) >= min_candidates:
            break
        # if filter_by_stack:
        #     filtered_df = df[df['Stack_Similarity'] >= consign_similarity_threshold]
        #     # Check if the number of filtered candidates meets the minimum requirement
        #     logger.info(f"number of candidates filter_by_stack {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        #     logger.info(filtered_df[["Full Name"]])
        #     if len(filtered_df) >= min_candidates:
        #         break
        # if filter_by_role:
        #     filtered_df = df[df['Role_Similarity'] >= consign_similarity_threshold]
        #     # Check if the number of filtered candidates meets the minimum requirement
        #     logger.info(f"number of candidates filter_by_role {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        #     logger.info(filtered_df[["Full Name"]])
        #     if len(filtered_df) >= min_candidates:
        #         break
        # Reduce the threshold for the next iteration
        consign_similarity_threshold -= 0.05

    filtered_df = filtered_df.drop(columns=['Embedding', 'Similarity'])

    return filtered_df, consign_similarity_threshold
