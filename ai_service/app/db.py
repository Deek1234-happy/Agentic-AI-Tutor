# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


# DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
# DATABASE_URL = "postgresql://ai:1234@pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com:18990/AgenticAITutor?sslmode=require"

# Read DATABASE_URL from .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Set schema search path
engine = create_engine(
    DATABASE_URL,
)
SessionLocal = sessionmaker(bind=engine)