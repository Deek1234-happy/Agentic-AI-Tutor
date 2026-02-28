# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://postgres:rehab%40postgres@localhost:5432/Agentic_AI_Tutor_GP"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
