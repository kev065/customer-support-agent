import os
import logging
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

logging.basicConfig(level=logging.INFO)
logging.getLogger("langchain").setLevel(logging.INFO)
logging.getLogger("openai").setLevel(logging.INFO)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise SystemExit("OPENAI_API_KEY not set in env")

llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=OPENAI_KEY)

resp = llm([HumanMessage(content="You are a support assistant. Briefly suggest 3 products good for hiking.")])
print("LLM response:\n", resp.content)