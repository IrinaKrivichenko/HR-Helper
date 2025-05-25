import warnings

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src.nlp.embedding_handler import add_embeddings_column

import os
from dotenv import load_dotenv
load_dotenv()



def filter_candidates_by_embedding(vacancy_info, df, embedding_handler, initial_threshold=0.8, min_threshold=0.3,
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

    print("shape of vacancy_embedding :", vacancy_embedding.shape)
    # Compute similarities with candidate embeddings
    # df['Similarity'] = df['Embedding'].apply(lambda x: cosine_similarity(vacancy_embedding, np.array(x).reshape(1, -1))[0][0])
    df['Similarity'] = df['Embedding'].apply(lambda x: cosine_similarity(vacancy_embedding, x)[0][0])
    # def cosine_similarity_debug(a, b):
    #     dot_product = np.dot(a, b)
    #     norm_a = np.linalg.norm(a)
    #     norm_b = np.linalg.norm(b)
    #     print(f"Dot product: {dot_product}, Norm a: {norm_a}, Norm b: {norm_b}")
    #     similarity = dot_product / (norm_a * norm_b)
    #     return similarity
    #
    # # Пример использования
    # df['Similarity'] = df.apply(
    #     lambda row: cosine_similarity_debug(vacancy_embedding, row['Embedding']),
    #     axis=1
    # )

    # df['Role_Similarity'] = df['Role_Embedding'].apply(lambda x: cosine_similarity(vacancy_role_embedding, np.array(x).reshape(1, -1))[0][0])
    # df['Stack_Similarity'] = df['Stack_Embedding'].apply(lambda x: cosine_similarity(vacancy_stack_embedding, np.array(x).reshape(1, -1))[0][0])

    # exact_candidate_exists = df[df['First Name'] == 'Taisija']
    # if not exact_candidate_exists.empty:
    #     similarity_value = exact_candidate_exists['Similarity'].values[0]
    #     print(f"Similarity for Taisija: {similarity_value}")
    #     similarity_value = exact_candidate_exists['Role_Similarity'].values[0]
    #     print(f"Role_Similarity for Taisija: {similarity_value}")
    #     similarity_value = exact_candidate_exists['Stack_Similarity'].values[0]
    #     print(f"Stack_Similarity for Taisija: {similarity_value}")
    # else:
    #     print("No candidate found with First Name 'Taisija'")

    # Выводим строки, где возникли проблемы
    problematic_rows = df[df['Similarity'].isna()]
    print(f"Number of problematic rows: {df['Similarity'].isna().sum()}")
    for _, row in problematic_rows.iterrows():
        print(f"First Name: {row['First Name'][:10]}, "
              f"Last Name: {row['Last Name'][:10]}, "
              f"Role: {row['Role'][:10]}, "
              f"Stack: {row['Stack'][:10]}, "
              f"Row in Spreadsheets: {row['Row in Spreadsheets']}, "
              f"Embedding: {str(row['Embedding'])[:10]}")

    pd.set_option('display.max_rows', 50)
    # Filter candidates based on the similarity threshold
    consign_similarity_threshold = initial_threshold
    while consign_similarity_threshold >= min_threshold:
        filtered_df = df[df['Similarity'] >= consign_similarity_threshold]
        # Check if the number of filtered candidates meets the minimum requirement
        print(
            f"number of candidates {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        print(filtered_df[["Full Name"]])
        if len(filtered_df) >= min_candidates:
            break
        # if filter_by_stack:
        #     filtered_df = df[df['Stack_Similarity'] >= consign_similarity_threshold]
        #     # Check if the number of filtered candidates meets the minimum requirement
        #     print(f"number of candidates filter_by_stack {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        #     print(filtered_df[["Full Name"]])
        #     if len(filtered_df) >= min_candidates:
        #         break
        # if filter_by_role:
        #     filtered_df = df[df['Role_Similarity'] >= consign_similarity_threshold]
        #     # Check if the number of filtered candidates meets the minimum requirement
        #     print(f"number of candidates filter_by_role {len(filtered_df)} with consign_similarity_threshold {consign_similarity_threshold}")
        #     print(filtered_df[["Full Name"]])
        #     if len(filtered_df) >= min_candidates:
        #         break
        # Reduce the threshold for the next iteration
        consign_similarity_threshold -= 0.05

    filtered_df = filtered_df.drop(columns=['Embedding', 'Similarity'])

    return filtered_df, consign_similarity_threshold
