
import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# path to env file 
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(CONFIG_DIR, '.env')

load_dotenv(dotenv_path=ENV_FILE_PATH)


class Settings(BaseSettings):
    database_url: str = Field(..., env='DATABASE_URL')
    qdrant_url: str = Field(..., env='QDRANT_URL')
    openai_api_key: Optional[str] = Field(None, env='OPENAI_API_KEY')

    langchain_api_key: Optional[str] = Field(None, env='LANGCHAIN_API_KEY')
    langchain_tracing_v2: Optional[bool] = Field(False, env='LANGCHAIN_TRACING_V2')
    langchain_project: Optional[str] = Field(None, env='LANGCHAIN_PROJECT')

    class Config:
        env_file = ENV_FILE_PATH
        extra = "ignore"


settings = Settings()
