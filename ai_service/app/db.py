# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com")
DB_PORT = os.getenv("DB_PORT", "18990")
DB_NAME = os.getenv("DB_NAME", "AgenticAlTutor")  # Note: lowercase L
DB_USER = os.getenv("DB_USER", "avnadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "content")  # Add schema

from urllib.parse import quote_plus
if DB_PASSWORD:
    DB_PASSWORD = quote_plus(DB_PASSWORD)

# DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
DATABASE_URL = "postgresql://avnadmin:AVNS_DhmEe0vYkfMSPZb63EV@pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com:18990/AgenticAITutor?sslmode=require"

# Set schema search path
engine = create_engine(
    DATABASE_URL,
)
SessionLocal = sessionmaker(bind=engine)