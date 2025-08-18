
import psycopg2
from faker import Faker
import random
import uuid
from agent.config import settings
import faker_commerce

def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS order_items CASCADE;")
        cur.execute("DROP TABLE IF EXISTS orders CASCADE;")
        cur.execute("DROP TABLE IF EXISTS products CASCADE;")
        cur.execute("DROP TABLE IF EXISTS users CASCADE;")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price NUMERIC(10, 2) NOT NULL,
            stock_quantity INTEGER NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id SERIAL PRIMARY KEY,
            order_number VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES users(user_id),
            order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) NOT NULL,
            total_amount NUMERIC(10, 2) NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id SERIAL PRIMARY KEY,
            order_id INTEGER REFERENCES orders(order_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity INTEGER NOT NULL,
            price NUMERIC(10, 2) NOT NULL
        );
        """)
        conn.commit()


import faker_commerce


def seed_data(conn, num_users=1000, num_products=500, num_orders=2000):
    fake = Faker()
    fake.add_provider(faker_commerce.Provider)
    with conn.cursor() as cur:
        # Seed Users
        for _ in range(num_users):
            cur.execute("INSERT INTO users (name, address) VALUES (%s, %s)", (fake.name(), fake.address()))

        # Get all user IDs
        cur.execute("SELECT user_id FROM users")
        user_ids = [row[0] for row in cur.fetchall()]

        # Seed Products
        for _ in range(num_products):
            cur.execute("INSERT INTO products (name, description, price, stock_quantity) VALUES (%s, %s, %s, %s)",
                        (fake.ecommerce_name(), fake.text(), random.uniform(10, 500), random.randint(0, 100)))

        # Get all product IDs
        cur.execute("SELECT product_id FROM products")
        product_ids = [row[0] for row in cur.fetchall()]

        # Seed Orders and Order Items
        for _ in range(num_orders):
            user_id = random.choice(user_ids)
            order_date = fake.date_time_this_decade()
            order_status = random.choice(['pending', 'shipped', 'delivered', 'cancelled'])
            order_number = f"ORD-{uuid.uuid4()}"
            cur.execute("INSERT INTO orders (order_number, user_id, order_date, status, total_amount) VALUES (%s, %s, %s, %s, 0) RETURNING order_id",
                        (order_number, user_id, order_date, order_status))
            order_id = cur.fetchone()[0]
            
            num_order_items = random.randint(1, 5)
            total_amount = 0
            for _ in range(num_order_items):
                product_id = random.choice(product_ids)
                quantity = random.randint(1, 3)
                cur.execute("SELECT price FROM products WHERE product_id = %s", (product_id,))
                price = cur.fetchone()[0]
                total_amount += price * quantity
                cur.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                            (order_id, product_id, quantity, price))
            
            cur.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (total_amount, order_id))

        conn.commit()

if __name__ == "__main__":
    conn = psycopg2.connect(settings.database_url)
    create_tables(conn)
    seed_data(conn)
    conn.close()
