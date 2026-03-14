# import psycopg2

# try:
#     conn = psycopg2.connect(
#         dbname="AgenticAITutor",
#         user="avnadmin",
#         password="AVNS_DhmEe0vYkfMSPZb63EV",
#         host="pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com",
#         port=18990
#     )
#     print("Connected successfully!")
# except Exception as e:
#     print("Error:", e)


import psycopg2
import os

DATABASE_URL = "postgresql://avnadmin:AVNS_DhmEe0vYkfMSPZb63EV@pg-239d7105-agenticaitutor-8ab6.j.aivencloud.com:18990/AgenticAITutor"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT 1;")
    result = cur.fetchone()

    print("Connection successful!")
    print("Test query result:", result)

    cur.close()
    conn.close()

except Exception as e:
    print("Connection failed!")
    print("Error:", e)