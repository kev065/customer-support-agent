import psycopg2
from qdrant_client import QdrantClient
from agent.config import settings

def get_postgres_connection():
    conn = psycopg2.connect(settings.database_url)
    return conn

def get_qdrant_client():
    client = QdrantClient(settings.qdrant_url)
    return client
