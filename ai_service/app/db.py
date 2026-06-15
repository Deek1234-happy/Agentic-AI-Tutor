# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()


# Read DATABASE_URL from .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Set schema search path
engine = create_engine(
    DATABASE_URL,
)
SessionLocal = sessionmaker(bind=engine)