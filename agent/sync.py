import uuid
import json
import select
from db import get_connection, update_last_sync_time
from qdrant_setup import vectorstore

TABLES = ["users", "orders", "products", "order_items"]
PRIMARY_KEYS = {
    "users": "user_id",
    "orders": "order_id",
    "products": "product_id",
    "order_items": "order_item_id"
}

BATCH_SIZE = 100  # batch size for Qdrant inserts

# Helper function to batch a list
def batch_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Sync a single row to Qdrant
def sync_row(table_name, row_dict):
    pk_column = PRIMARY_KEYS[table_name]
    row_id = row_dict[pk_column]

    point_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}_{row_id}")
    texts = [json.dumps(row_dict)]
    metadatas = [{"table": table_name, "pk": row_id}]
    ids = [point_id]

    try:
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        update_last_sync_time(table_name)
        print(f"Synced {table_name} row {row_id}")
    except Exception as e:
        print(f"Failed to sync {table_name} row {row_id}: {e}")

# Main sync listener
def main():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Listen to all table channels
    for table_name in TABLES:
        cursor.execute(f"LISTEN {table_name}_changed;")
    print("Sync agent listening for changes. Press Ctrl+C to stop.")

    try:
        while True:
            # Wait for notifications
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = json.loads(notify.payload)
                table = notify.channel.replace("_changed", "")
                sync_row(table, payload)
    except KeyboardInterrupt:
        print("\nSync agent stopped by user.")
    finally:
        cursor.close()
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
