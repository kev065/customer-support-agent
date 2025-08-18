
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

from agent.config import settings


def get_qdrant_retriever():
    """
    Initializes and returns a Qdrant vector store retriever.
    """
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
    client = QdrantClient(url=settings.qdrant_url)

    vector_store = Qdrant(
        client=client,
        collection_name="products",
        embeddings=embeddings,
    )
    
    return vector_store.as_retriever()
