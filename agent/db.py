import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="mydatabase2",
        user="store_user",
        password="password",
        host="localhost",
        port=5432,
    )

def get_last_sync_time(table_name): ...
def update_last_sync_time(table_name): ...
