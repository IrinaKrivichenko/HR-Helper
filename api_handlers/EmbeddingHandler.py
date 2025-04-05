import tiktoken
import os
import numpy as np
import faiss
from openai import OpenAI, AuthenticationError, OpenAIError
from dotenv import load_dotenv

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
            faiss.normalize_L2(embedding)
            return embedding
        except AuthenticationError:
            raise Exception("An AuthenticationError occurred. The API key used for authentication might be invalid.")
        except OpenAIError:
            raise Exception("An OpenAIError occurred. There might be an issue with the connection.")
