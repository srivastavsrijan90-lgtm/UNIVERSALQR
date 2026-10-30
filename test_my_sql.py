import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1111",
        database="universal_qr",
        port=3306
    )

    if connection.is_connected():
        print("MySQL connected successfully!")

        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        print("Tables:", cursor.fetchall())

        cursor.close()
        connection.close()

except Error as error:
    print("MySQL connection failed:", error)