import psycopg2
import os
import streamlit as st

def get_connection():
    config = {
        "host": os.getenv("ECOSPACE_DB_HOST"),
        "port": os.getenv("ECOSPACE_DB_PORT"),
        "dbname": os.getenv("ECOSPACE_DB_NAME"),
        "user": os.getenv("ECOSPACE_DB_USER"),
        "password": os.getenv("ECOSPACE_DB_PASSWORD"),
    }
    if not all(config.values()):
        config = dict(st.secrets["postgres"])
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"]
    )
    cursor = conn.cursor()
    return conn, cursor
