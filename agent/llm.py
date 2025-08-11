
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import settings

def get_llm():
    return ChatOpenAI(api_key=settings.openai_api_key)

def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "{question}")
    ])
    chain = prompt | get_llm() | StrOutputParser()
    return chain
