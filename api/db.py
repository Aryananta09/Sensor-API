import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # ganti sesuai setting MySQL
        password="",        # isi kalau ada password
        database="intern_telkomsel"
    )

