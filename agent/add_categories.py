from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from pydantic import BaseModel, Field
from enum import Enum
import hashlib

# 1. Setup Postgres connection
engine = create_engine("postgresql://store_user:password@localhost:5432/mydatabase2")

# 2. Define schema for classification
class CategoryEnum(str, Enum):
    smartphones = "smartphones"
    laptops = "laptops"
    watches = "watches"
    accessories = "accessories"
    tvs = "tvs"
    monitors = "monitors"
    audio = "audio"
    wearables = "wearables"
    networking = "networking"
    printers = "printers"
    cameras = "cameras"
    drones = "drones"
    storage = "storage"
    peripherals = "peripherals"
    smart_home = "smart_home"
    consoles = "consoles"
    other = "other"

class ProductCategory(BaseModel):
    category: CategoryEnum = Field(..., description="The product category.")

# 3. Setup LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(ProductCategory)

# 4. Dynamic category list for the prompt
CATEGORY_LIST = ", ".join([c.value for c in CategoryEnum])

tagging_prompt = ChatPromptTemplate.from_template(
    f"""
Classify the following product into ONE of these categories:
{CATEGORY_LIST}

Product:
Name: {{name}}
Description: {{description}}
"""
)

# 5. Utility: checksum for deduplication
def make_checksum(name: str, description: str) -> str:
    text = (name or "") + "|" + (description or "")
    return hashlib.md5(text.encode("utf-8")).hexdigest()

# 6. Classification function
def classify_product(name: str, description: str) -> str:
    # truncate to save tokens
    desc_short = (description or "")[:200]
    prompt = tagging_prompt.invoke({"name": name, "description": desc_short})
    result = llm.invoke(prompt)
    return result.category

# 7. Ensure schema exists
def ensure_schema():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS category TEXT"))
            conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS category_checksum TEXT"))
            conn.commit()
        except ProgrammingError:
            pass

# 8. Processing pipeline
def process_products(batch_size=228):
    ensure_schema()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT product_id, name, description, category, category_checksum
            FROM products
            WHERE category IS NULL
               OR category_checksum IS NULL
               OR category_checksum != md5(coalesce(name,'') || '|' || coalesce(description,''))
            LIMIT :limit
        """), {"limit": batch_size}).fetchall()

        for row in rows:
            product_id, name, description, category, old_checksum = row
            checksum = make_checksum(name, description)

            new_category = classify_product(name, description)

            conn.execute(
                text("""
                    UPDATE products
                    SET category=:c, category_checksum=:chk
                    WHERE product_id=:i
                """),
                {"c": new_category, "chk": checksum, "i": product_id}
            )
            conn.commit()
            print(f"✅ Product {product_id} classified as {new_category}")

    print(f"🎉 Finished processing {len(rows)} products.")

if __name__ == "__main__":
    process_products(batch_size=228)
