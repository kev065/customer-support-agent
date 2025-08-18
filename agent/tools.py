

import logging
from typing import List

import psycopg
from langchain.tools import tool
from langchain.tools.retriever import create_retriever_tool
from psycopg.rows import dict_row

from agent.config import settings
from agent.retrievers import get_qdrant_retriever

# --- Qdrant Retriever Tool ---

# First, create the base retriever from our Qdrant vector store
qdrant_retriever = get_qdrant_retriever()

# Now, create a tool that uses this retriever
# The description is critical for the agent to know when to use this tool
product_search_tool = create_retriever_tool(
    retriever=qdrant_retriever,
    name="product_semantic_search",
    description="Use this tool to search for products based on a semantic description. "
                "For example, you can ask 'what do you have that is good for hiking?' "
                "or 'do you have any waterproof jackets?' The input is a query describing the product."
)

# --- PostgreSQL Order Details Tool ---

@tool
def get_order_details(order_id: int) -> str:
    """Use this tool to get the details of a specific order by its ID. 
    This includes the order status, date, total amount, and a list of items in the order. 
    Requires the integer order_id.
    """
    logging.info(f"Executing get_order_details for order_id: {order_id}")
    sql = """
        SELECT 
            o.order_id, o.order_date, o.status, o.total_amount,
            oi.quantity, p.name as product_name, p.price as product_price
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.order_id = %s;
    """
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (order_id,))
                results = cur.fetchall()

        if not results:
            return f"No order found with ID {order_id}."

        # Format the results into a readable string for the LLM
        order = results[0]
        order_summary = (
            f"Order ID: {order['order_id']}\n"
            f"Status: {order['status']}\n"
            f"Date: {order['order_date'].strftime('%Y-%m-%d')}\n"
            f"Total Amount: ${order['total_amount']}\n\n"
            f"Items:\n"
        )
        
        items_details = []
        for row in results:
            item_str = f"  - Product: {row['product_name']}, Quantity: {row['quantity']}, Price: ${row['product_price']}"
            items_details.append(item_str)
        
        return order_summary + "\n".join(items_details)

    except Exception as e:
        logging.error(f"Error fetching order details for order_id {order_id}: {e}")
        return "An error occurred while trying to fetch order details. Please try again."


# --- List of all tools for the agent ---

all_tools: List = [product_search_tool, get_order_details]


