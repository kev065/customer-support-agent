
from fastapi import FastAPI
from .database import get_postgres_connection, get_qdrant_client
from .llm import get_chain
from .retrievers import get_postgres_data, get_qdrant_retriever

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    app.state.db_connection = get_postgres_connection()
    app.state.qdrant_client = get_qdrant_client()
    app.state.llm_chain = get_chain()
    app.state.qdrant_retriever = get_qdrant_retriever()

@app.on_event("shutdown")
async def shutdown_event():
    app.state.db_connection.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/status")
def get_status():
    return {"postgres_status": "connected" if app.state.db_connection else "disconnected",
            "qdrant_status": "connected" if app.state.qdrant_client else "disconnected"}

@app.post("/chat")
async def chat(question: str):
    response = app.state.llm_chain.invoke({"question": question})
    return {"response": response}

@app.post("/query_postgres")
def query_postgres(query: str):
    data = get_postgres_data(query)
    return {"data": data}

@app.post("/query_qdrant")
def query_qdrant(query: str):
    # This is a placeholder for the actual Qdrant query logic.
    return {"data": "Qdrant retriever not implemented yet."}
