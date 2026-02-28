import psycopg2

try:
    conn = psycopg2.connect(
        dbname="ai_tutor",
        user="postgres",
        password="123",
        host="127.0.0.1",
        port=5433
    )
    print("Connected successfully!")
except Exception as e:
    print("Error:", e)
