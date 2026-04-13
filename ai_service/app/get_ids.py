# get_ids.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from sqlalchemy import text

def get_all_ids():
    db = SessionLocal()
    try:
        # Get all users
        users = db.execute(text("""
            SELECT id, first_name, last_name, email 
            FROM auth.users 
            ORDER BY created_at DESC
        """)).fetchall()
        
        print("\n" + "="*60)
        print("USERS")
        print("="*60)
        for u in users:
            print(f"ID: {u[0]}")
            print(f"Name: {u[1]} {u[2]}")
            print(f"Email: {u[3]}")
            print("-"*40)
        
        # Get all subjects
        subjects = db.execute(text("""
            SELECT id, name, user_id 
            FROM content.subjects 
            ORDER BY name
        """)).fetchall()
        
        print("\n" + "="*60)
        print("SUBJECTS")
        print("="*60)
        for s in subjects:
            print(f"ID: {s[0]}")
            print(f"Name: {s[1]}")
            print(f"User ID: {s[2]}")
            print("-"*40)
        
        # Get all documents
        docs = db.execute(text("""
            SELECT id, filename, user_id, subject_id 
            FROM content.documents 
            WHERE is_deleted = false
            ORDER BY upload_time DESC
            LIMIT 20
        """)).fetchall()
        
        print("\n" + "="*60)
        print("DOCUMENTS (last 20)")
        print("="*60)
        for d in docs:
            print(f"ID: {d[0]}")
            print(f"File: {d[1]}")
            print(f"User ID: {d[2]}")
            print(f"Subject ID: {d[3]}")
            print("-"*40)
            
    finally:
        db.close()

if __name__ == "__main__":
    get_all_ids()