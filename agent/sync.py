import logging
import select
import json

import psycopg
from psycopg.rows import dict_row
from qdrant_client import QdrantClient, models

from agent.config import settings
from agent.llm import get_embeddings

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Qdrant configuration
QDRANT_COLLECTION_NAME = "products"
VECTOR_SIZE = 1536 # OpenAI's text-embedding-ada-002

# PostgreSQL notification channel
PG_CHANNEL_NAME = "product_changes"


class PostgresListener:
    """
    Listens for notifications from Postgres and syncs changes to Qdrant.
    """

    def __init__(self):
        self.qdrant_client = QdrantClient(url=settings.qdrant_url)
        self.embedding_function = get_embeddings()
        self._setup_qdrant_collection()

    def _setup_qdrant_collection(self):
        """Ensures the Qdrant collection exists."""
        if self.qdrant_client.collection_exists(collection_name=QDRANT_COLLECTION_NAME):
            logging.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' already exists.")
        else:
            logging.info(f"Creating Qdrant collection: '{QDRANT_COLLECTION_NAME}'")
            self.qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
            )

    def _get_product_by_id(self, product_id: int) -> dict | None:
        """Fetches a single product from the database."""
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM products WHERE product_id = %s;", (product_id,))
                return cur.fetchone()

    def _handle_notification(self, payload: str):
        """Processes a notification payload from Postgres."""
        try:
            data = json.loads(payload)
            operation = data.get("operation")
            product_id = data.get("id")

            if not all([operation, product_id]):
                logging.warning(f"Invalid payload received: {payload}")
                return

            logging.info(f"Received {operation} for product ID: {product_id}")

            if operation == "DELETE":
                self.qdrant_client.delete(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points_selector=models.PointIdsList(points=[product_id]),
                    wait=True,
                )
                logging.info(f"Deleted product {product_id} from Qdrant.")
            
            else: # INSERT or UPDATE
                product_data = self._get_product_by_id(product_id)
                if not product_data:
                    logging.error(f"Could not find product with ID {product_id} after notification.")
                    return

                text_to_embed = f"Product: {product_data.get('name', '')}\nDescription: {product_data.get('description', '')}"
                vector = self.embedding_function.embed_query(text_to_embed)

                self.qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=[
                        models.PointStruct(
                            id=product_id,
                            vector=vector,
                            payload=product_data,
                        )
                    ],
                    wait=True,
                )
                logging.info(f"Upserted product {product_id} into Qdrant.")

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Failed to process notification: {e}\nPayload: {payload}")

    def listen(self):
        """Connects to Postgres and enters a loop to listen for notifications."""
        logging.info("Starting Postgres listener...")
        with psycopg.connect(settings.database_url, autocommit=True) as conn:
            conn.execute(f"LISTEN {PG_CHANNEL_NAME};")
            logging.info(f"Listening on channel '{PG_CHANNEL_NAME}'.")

            while True:
                # Use select to wait for notifications without blocking
                select.select([conn.fileno()], [], [], 60) # 60s timeout
                for notify in conn.notifies():
                    self._handle_notification(notify.payload)

if __name__ == "__main__":
    listener = PostgresListener()
    listener.listen()