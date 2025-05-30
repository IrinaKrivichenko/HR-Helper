import numpy as np
import pandas as pd
# import faiss
from openai import OpenAI, AuthenticationError, OpenAIError

from src.google_services.sheets import write_specific_columns

import os
from dotenv import load_dotenv

from src.logger import logger

load_dotenv()

class EmbeddingHandler:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.EMBEDDING_MODEL = "text-embedding-3-large"

    def get_text_embedding(self, text: str) -> np.array:
        try:
            response = self.openai_client.embeddings.create(input=text, model=self.EMBEDDING_MODEL)
            embedding = response.data[0].embedding
            embedding = np.array(embedding)
            embedding = embedding.astype("float32")
            embedding = np.expand_dims(embedding, axis=0)
            # faiss.normalize_L2(embedding)
            return embedding
        except AuthenticationError:
            raise Exception("An AuthenticationError occurred. The API key used for authentication might be invalid.")
        except OpenAIError:
            raise Exception("An OpenAIError occurred. There might be an issue with the connection.")

def string_to_array(s):
    if isinstance(s, str) and s.strip():
        # Remove brackets and split characters into elements.
        s = s.replace("[", "").replace("]", "")
        elements = np.fromstring(s, sep=' ')
        # return elements.reshape(1, -1)  # Assuming it's a 2D array with one row
        return elements  # Return a 1D array
    return s

def add_embeddings_column(df, write_columns=False):
    """
    Adds 'Embedding', 'Role_Embedding', and 'Stack_Embedding' columns to the DataFrame if they don't exist,
    calculates embeddings for rows where 'Embedding', 'Role_Embedding', or 'Stack_Embedding' is empty,
    and writes the updated DataFrame back to the Google Sheet.

    Args:
    - df (pd.DataFrame): DataFrame containing the data to process.
    """
    # Check if 'Embedding', 'Role_Embedding', and 'Stack_Embedding' columns exist, if not, create them
    if 'Embedding' not in df.columns:
        df['Embedding'] = ""
    if 'Role_Embedding' not in df.columns:
        df['Role_Embedding'] = ""
    if 'Stack_Embedding' not in df.columns:
        df['Stack_Embedding'] = ""

    np.set_printoptions(threshold=np.inf, linewidth=np.inf)

    # Initialize the embedding handler
    embedding_handler = EmbeddingHandler()

    df['Embedding'] = df['Embedding'].astype(object)
    # Calculate embeddings for rows where 'Embedding', 'Role_Embedding', or 'Stack_Embedding' is empty
    for index, row in df.iterrows():
        if str(row['Embedding']) == "":
            # Concatenate text fields to create a single string for embedding
            text_fields = [row['Role'], row['Stack'], row['Industry'], row['Expertise'], row['Location']]
            text_for_embedding = " ".join(str(field) for field in text_fields if pd.notna(field))
            if text_for_embedding:
                embedding = embedding_handler.get_text_embedding(text_for_embedding)
                # Assign the embedding to the DataFrame
                df.at[index, 'Embedding'] = str(embedding)

        # if str(row['Role_Embedding']) == "" and pd.notna(row['Role']):
        #     # Calculate embedding for 'Role'
        #     role_embedding = embedding_handler.get_text_embedding(str(row['Role']))
        #     logger.info('Role Embedding length', len(role_embedding[0]))
        #     df.at[index, 'Role_Embedding'] = role_embedding

        # if str(row['Stack_Embedding']) == "" and pd.notna(row['Stack']):
        #     # Calculate embedding for 'Stack'
        #     stack_embedding = embedding_handler.get_text_embedding(str(row['Stack']))
        #     logger.info('Stack Embedding length', len(stack_embedding[0]))
        #     df.at[index, 'Stack_Embedding'] = stack_embedding

    # Write the updated DataFrame back to the Google Sheet
    if write_columns:
        # write_specific_columns(df[['Embedding', 'Role_Embedding', 'Stack_Embedding']])
        write_specific_columns(df[['Embedding']])
    df['Embedding'] = df['Embedding'].apply(string_to_array)
    logger.info(f"Embedding shape: {df['Embedding'][0].shape}")
    return df




