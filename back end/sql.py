import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password, db_name):
    """
    Create a database connection to a MySQL server.
    Returns the connection object, or None if it fails.
    """
    try:
        conn = mysql.connector.connect(
            host=host_name,
            user=user_name,
            password=user_password,  
            database=db_name,
            port=3306
        )
        return conn
    except Error as e:
        print(f"[DB CONNECT ERROR] {e}")
        return None


def execute_read_query(connection, query):
    """
    Execute a SELECT query and return all results as a list of dicts.
    """
    if connection is None:
        raise RuntimeError("DB connection is None (create_connection failed).")

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    except Error as e:
        print(f"[DB QUERY ERROR] {e}")
        return []