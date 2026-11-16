
import os
import pymysql
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA_CERT_PATH = os.path.join(BASE_DIR, "certs", "ca.pem")


def get_config(name, default=None):
    # First, check environment variables (.env locally)
    value = os.getenv(name)

    if value is not None:
        return value

    # Otherwise, check Streamlit Cloud Secrets
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return default


def get_connection():
    return pymysql.connect(
        host=get_config("DB_HOST"),
        port=int(get_config("DB_PORT", "4000")),
        user=get_config("DB_USER"),
        password=get_config("DB_PASSWORD"),
        database=get_config("DB_NAME"),
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        ssl_ca=CA_CERT_PATH,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15
    )
