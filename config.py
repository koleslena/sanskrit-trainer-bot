import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

class Settings(BaseSettings):
    
    # Бот
    BOT_TOKEN: str
    
    # LLM
    OPENROUTER_API_KEY: str
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1"
    MODEL_NAME: str = "openai/gpt-4o-mini"
    
    # БД 
    DB_HOST: str 
    DB_PORT: int 
    DB_USER: str 
    DB_PASSWORD: str 
    DB_NAME: str 

    # Конфигурация Pydantic
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # игнорировать лишние переменные в .env
    )

# Создаем один экземпляр настроек для всего приложения
settings = Settings()