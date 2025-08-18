from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from agent.llm import create_agent_graph


app = FastAPI()

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # The address of your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create the LangGraph agent graph
agent_graph = create_agent_graph()

# Initialize a CopilotKit remote endpoint and register the LangGraph agent
sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="customer_support_agent",
            description="Hyper-aware customer support agent backed by Postgres and Qdrant",
            graph=agent_graph,
        )
    ]
)

# Mount the CopilotKit endpoint at /copilotkit
add_fastapi_endpoint(app, sdk, "/copilotkit", use_thread_pool=False)


@app.get("/health")
def health():
    return {"status": "ok"}
