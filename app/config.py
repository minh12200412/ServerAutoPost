# app/config.py
import os
from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./licenses.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 365
    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS: str = os.getenv("ADMIN_PASS", "123456")

settings = Settings()
