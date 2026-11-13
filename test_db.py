
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

try:
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()

        print("Database connected successfully!")
        print("Connected Database:", result[0])

    connection.close()

except Exception as error:
    print("Database connection failed!")
    print("Error:", error)
