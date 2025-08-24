import os
import uuid
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
COLLECTION_NAME = "postgres_v2"
BATCH_SIZE = 1000 

# pg connect
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# see all user tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type='BASE TABLE';
""")
tables = [row[0] for row in cur.fetchall()]
print(f"Found tables: {tables}")

# Setup Qdrant client and embeddings
qdrant = QdrantClient(url=QDRANT_URL)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )
    print(f"Created collection {COLLECTION_NAME}")
else:
    print(f"ℹCollection {COLLECTION_NAME} already exists, skipping creation.")

vectorstore = QdrantVectorStore(
    client=qdrant,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)

for table in tables:
    # Find primary key column
    cur.execute(sql.SQL("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid
                          AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass
        AND i.indisprimary;
    """), [table])
    pk_row = cur.fetchone()
    if not pk_row:
        print(f"Skipping table {table}: no primary key found.")
        continue

    pk_col = pk_row[0]
    print(f"Processing {table}, primary key = {pk_col}")

    # Count rows
    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
    row = cur.fetchone()
    total_rows = row[0] if row is not None else 0


    for offset in range(0, total_rows, BATCH_SIZE):
        cur.execute(
            sql.SQL("SELECT * FROM {} ORDER BY {} LIMIT %s OFFSET %s")
            .format(sql.Identifier(table), sql.Identifier(pk_col)),
            (BATCH_SIZE, offset)
        )
        rows = cur.fetchall()
        if not rows or cur.description is None:
            continue

        colnames = [desc[0] for desc in cur.description]

        texts, metadatas, ids = [], [], []

        for row in rows:
            row_dict = dict(zip(colnames, row))
            pk_value = row_dict[pk_col]

            # Structured fields so it can be is able to be searched and filterable
            searchable_fields = {
                "price": row_dict.get("price"),
                "category": row_dict.get("category"),
                "stock_quantity": row_dict.get("stock_quantity"),
            }

            # columns to skip for embedding text
            SKIP_COLS = {
                "order_item_id", "order_id", "product_id", "quantity",
                "order_id", "order_number", "user_id", "order_date",
                "product_id", "category_checksum", "user_id", "created_at",
                "price", "total_amount", "stock_quantity"  # these go in structured metadata
            }

            text_parts = []
            for col, val in row_dict.items():
                if val is None or col in SKIP_COLS:
                    continue
                text_parts.append(f"{col}: {val}")

            text = " | ".join(text_parts)

            # Build metadata (structured + fallback info)
            metadata = {
                "table": table,
                "primary_key": pk_value,
                **searchable_fields,    # explicitly stored structured fields
            }


            # Stable unique IDs
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{table}_{pk_value}"))

            texts.append(text)
            metadatas.append(metadata)
            ids.append(point_id)

        # Upsert batch into Qdrant (hybrid)
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        print(f"Inserted batch {offset}-{offset+len(rows)} of {table}")

cur.close()
conn.close()
print("All tables processed.")
