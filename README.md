
# Customer Support Agent

AI-powered customer support agent for an e-commerce platform. It uses openai and a combination of structured and vector databases to provide context-rich, accurate, and helpful responses to customer queries.

## Key Features

- **Real-time Customer Support:** An interactive repl chat interface for customers to get help.
- **Context-Aware Responses:** uses data from order history, product information to inform its answers.
- **Semantic Search:** Utilizes a Qdrant as the vector database to perform semantic searches over product descriptions and other unstructured data.
- **Persistent Data Sync:** A real-time synchronization service keeps the Qdrant vector store perfectly in sync with the primary postgres database.

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

### 2. Set up Qdrant

Start the Qdrant vector database using Docker or Podman. This command will persist your data in a `qdrant_storage` directory in your project root.

```bash
# Using Podman
podman run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage:z qdrant/qdrant

# Or using Docker
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

### 3. Set up the env (`agent/`)

- **Create Virtual Environment:**
  ```bash
  python3 -m venv agent/venv
  source agent/venv/bin/activate
  ```

- **Install Dependencies:**
  ```bash
  pip install -r agent/requirements.txt
  ```

- **Configure Environment Variables:**
  Create a file named `.env` inside the `agent/` directory (`agent/.env`) and add the following, replacing the placeholder values:
  ```dotenv
  DATABASE_URL="postgresql://your_user:your_password@localhost:5432/your_db"
  QDRANT_URL="http://localhost:6333"
  OPENAI_API_KEY="your-openai-api-key"
  LANGCHAIN_API_KEY="your-langchain-api-key"
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_PROJECT=CUSTOMER_SUPPORT
  ```

## Running the Application

To run the full application, you will need to start 2 separate terminals.

- **Terminal 1: Qdrant Server**
  ```bash
  podman run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage:z qdrant/qdrant
  ```

- **Terminal 2: customer service agent**
  ```bash
  source agent/venv/bin/activate
  python3 agent/customer_support_agent.py
  ```

  ```
