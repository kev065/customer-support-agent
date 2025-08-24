from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "postgres_v2"

qdrant = QdrantClient(url=QDRANT_URL)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# checks before creating
# if not qdrant.collection_exists(COLLECTION_NAME):
#     qdrant.create_collection(
#         collection_name=COLLECTION_NAME,
#         vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
#     )

vectorstore = QdrantVectorStore(
    client=qdrant,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)
