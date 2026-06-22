import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="flores_patagonia",
        user="TUUSER",
        password="TUPASSWORD"
    )