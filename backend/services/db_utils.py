import os
import threading

import pymysql

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "xL4noaDNexXCSseoqWHE")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_SOCKET = os.getenv("DB_SOCKET", "/var/run/mysqld/mysqld.sock")

_db_lock = threading.Lock()


def quote_ident(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def connect_mysql() -> pymysql.Connection:
    host_norm = DB_HOST.strip().lower()
    common = {
        "user": DB_USER,
        "password": DB_PASS,
        "database": DB_NAME,
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor,
    }
    if host_norm in {"localhost", "localhostl"}:
        return pymysql.connect(unix_socket=DB_SOCKET, **common)
    return pymysql.connect(host=DB_HOST, port=DB_PORT, **common)


def db_lock() -> threading.Lock:
    return _db_lock
