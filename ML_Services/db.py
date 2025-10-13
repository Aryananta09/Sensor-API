from mysql.connector import pooling

dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "intern_telkomsel"
}

connection_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)

def get_connection():
    return connection_pool.get_connection()

