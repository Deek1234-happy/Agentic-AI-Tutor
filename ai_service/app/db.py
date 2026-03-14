# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://avnadmin:AVNS_DhmEe0vYkfMSPZb63EV@pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com:18990/AgenticAITutor"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
