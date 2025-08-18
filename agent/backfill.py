

import logging

import psycopg
from psycopg.rows import dict_row
from qdrant_client import QdrantClient, models

from agent.config import settings
from agent.llm import get_embeddings

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

QDRANT_COLLECTION_NAME = "products"
BATCH_SIZE = 128  # Process records in batches for efficiency


def backfill_products():
    """
    Reads all products from Postgres, creates embeddings, and upserts them to Qdrant.
    """
    qdrant_client = QdrantClient(url=settings.qdrant_url)
    embedding_function = get_embeddings()

    logging.info("Starting backfill process for products...")

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT * FROM products ORDER BY product_id;")
                
                total_products = 0
                while True:
                    batch = cur.fetchmany(BATCH_SIZE)
                    if not batch:
                        break

                    total_products += len(batch)
                    logging.info(f"Processing batch of {len(batch)} products...")

                    points_to_upsert = []
                    for product in batch:
                        text_to_embed = f"Product: {product.get('name', '')}\nDescription: {product.get('description', '')}"
                        
                        vector = embedding_function.embed_query(text_to_embed)
                        
                        points_to_upsert.append(
                            models.PointStruct(
                                id=product['product_id'],
                                vector=vector,
                                payload=dict(product), # Use the whole product row as payload
                            )
                        )
                    
                    if points_to_upsert:
                        qdrant_client.upsert(
                            collection_name=QDRANT_COLLECTION_NAME,
                            points=points_to_upsert,
                            wait=True,
                        )
                        logging.info(f"Successfully upserted {len(points_to_upsert)} points to Qdrant.")

        logging.info(f"Backfill complete. Total products processed: {total_products}.")

    except psycopg.Error as e:
        logging.error(f"A database error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Note: Ensure your Qdrant collection is created before running this.
    # The sync.py script already handles this, so it's best to run it at least once first.
    backfill_products()
