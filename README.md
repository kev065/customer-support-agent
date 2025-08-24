
# Customer Support Agent

AI-powered customer support agent for an e-commerce platform. It uses openai and a combination of structured and vector databases to provide context-rich, accurate, and helpful responses to customer queries.

## Key Features

- **Real-time Customer Support:** An interactive repl chat interface for customers to get help.
- **Context-Aware Responses:** uses data from order history, product information to inform its answers.
- **Semantic Search:** Utilizes a Qdrant as the vector database to perform semantic searches over product descriptions and other unstructured data.

## Tech Stack

  - [LangChain](https://www.langchain.com/): framework for orchestrating LLM logic.
  - [PostgreSQL](https://www.postgresql.org/): the primary structured database for customers, orders, products, etc.
  - [Qdrant](https://qdrant.tech/): the vector database for storing and searching embeddings.
  - [OpenAI](https://openai.com/): provides the core LLM and text embedding models.

## Architecture Overview

The system is composed of several key components that work together:

- **`agent/customer_support_agent.py`:** python script that serves as the main file for the interactive shell. handles all LLM-related logic using LangChain, and communicates with the Postgres and Qdrant databases to handle customer queies.

- **`agent/sync.py` (Real-time Sync Service):** background service that listens for changes in the Postgres database using the `NOTIFY`/`LISTEN` mechanism. When a record (e.g., a product) is created, updated, or deleted, this service immediately processes the change, generates a new vector embedding if necessary, and upserts or deletes the corresponding entry in Qdrant.

- **`agent/embed.py` (Data Embedding Script):** A one-time script used to populate the Qdrant database with embeddings from all the existing data in Postgres.

## Setup and Installation

### Prerequisites

- [Git](https://git-scm.com/)
- [Python 3.10+](https://www.python.org/)
- [Docker](https://www.docker.com/) or [Podman](https://podman.io/) (for running Qdrant)

### 1. Clone the Repository

```bash
git clone git@github.com:kev065/customer-support-agent.git
cd customer-support-agent
```

### 2. Set up the environment

- **Create Virtual Environment:**
  ```bash
  python3 -m venv agent/venv
  source agent/venv/bin/activate
  ```

- **Install Dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

- **Configure Environment Variables:**
  Create a file named `.env` inside the `agent/` directory (`agent/.env`) and add the following, replacing the placeholder values:
  ```dotenv
  DATABASE_URL="postgresql://store_user:password@localhost:5432/mydatabase2"
  QDRANT_URL="http://localhost:6333"
  OPENAI_API_KEY="your-openai-api-key"
  LANGCHAIN_API_KEY="your-langchain-api-key"
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_PROJECT=CUSTOMER_SUPPORT
  ```

### 3. Set up PostgreSQL

create the database 'mydatabase2' and user 'store_user' inside postgres.
  ``` 
-- log into postgres as a superuser
sudo -u postgres psql 
\c postgres;

-- create the database
CREATE DATABASE mydatabase2;

-- create the user with a password
CREATE USER store_user WITH PASSWORD password;

-- grant privileges
GRANT ALL PRIVILEGES ON DATABASE mydatabase2 TO store_user;
  ```

Point your seed script to use store_user. in your shell:

``` 
export DATABASE_URL="postgresql+psycopg2://store_user:password@localhost:5432/mydatabase2"
```

Run seed script:
```bash
python3 agent/seed.py
```

Run add_categories.py. Uses open ai to classify all products into categories. This adds a 'category' column to all products in the db
```bash
python3 agent/add_categories.py
```

Run the embedding script to populate Qdrant with initial data:
```bash
python3 agent/embed.py
```

### 4. Set up Qdrant
Pull the qdrant image

```bash
podman pull qdrant/qdrant
```

For embeddings to survive machine restarts:

```
mkdir -p ./qdrant_data
```

Start the Qdrant vector database using Docker or Podman. This command will persist your data in a `qdrant_storage` directory in your project root.

```bash
# Using Podman
podman run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage:z qdrant/qdrant

# Or using Docker
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

## Running the Application

To run the application, run the following commands in a python environment.

  ```bash
  source agent/venv/bin/activate
  python3 agent/customer_support_agent.py
  ```

  In the interactive shell, you can now start asking questions related to customer support. The agent will intelligently route your queries to the appropriate service (SQL or vector search) based on the content of your questions.

  Try asking these questions:
  - "What is the status of order 28?"
  - "Tell me about the watches you sell"
  - "What are your return policies?"
  - "Can you recommend some phones i can buy that you sell"
  - "How do I track my shipment?"
