
import os
from pydantic_settings import BaseSettings

# Build an absolute path to the .env file, assuming it's in the same
# directory as this config.py file.
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE_PATH = os.path.join(CONFIG_DIR, '.env')

class Settings(BaseSettings):
    database_url: str
    qdrant_url: str
    openai_api_key: str

    class Config:
        env_file = ENV_FILE_PATH
        extra = "ignore"

settings = Settings()
