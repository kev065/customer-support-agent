
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Build an absolute path to the .env file (agent/.env)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(CONFIG_DIR, '.env')

# Load .env explicitly using python-dotenv so runtime and tooling that rely
# on dotenv will see the variables right away.
load_dotenv(dotenv_path=ENV_FILE_PATH)


class Settings(BaseSettings):
    # Core services
    database_url: str = Field(..., env='DATABASE_URL')
    qdrant_url: str = Field(..., env='QDRANT_URL')
    openai_api_key: Optional[str] = Field(None, env='OPENAI_API_KEY')

    # LangChain related environment variables present in your .env
    langchain_api_key: Optional[str] = Field(None, env='LANGCHAIN_API_KEY')
    langchain_tracing_v2: Optional[bool] = Field(False, env='LANGCHAIN_TRACING_V2')
    langchain_project: Optional[str] = Field(None, env='LANGCHAIN_PROJECT')

    class Config:
        # keep env_file here for compatibility with pydantic tooling
        env_file = ENV_FILE_PATH
        extra = "ignore"


settings = Settings()
