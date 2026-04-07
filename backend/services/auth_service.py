import hashlib
import hmac
import os
from typing import Any

from backend.services.db_utils import connect_mysql, quote_ident


class AuthService:
    def __init__(self, table_name: str = "admin_users") -> None:
        self.table_name = table_name

    def ensure_table(self) -> None:
        conn = connect_mysql()
        try:
            ddl = f"""
            CREATE TABLE IF NOT EXISTS {quote_ident(self.table_name)} (
                id BIGINT NOT NULL AUTO_INCREMENT,
                email VARCHAR(190) NOT NULL,
                username VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY uk_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            with conn.cursor() as cursor:
                cursor.execute(ddl)
        finally:
            conn.close()

    @staticmethod
    def _hash_password(password: str, salt_hex: str | None = None) -> str:
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
        return f"{salt.hex()}${hashed.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        try:
            salt_hex, hash_hex = password_hash.split("$", 1)
        except ValueError:
            return False
        calc = AuthService._hash_password(password, salt_hex=salt_hex)
        return hmac.compare_digest(calc.split("$", 1)[1], hash_hex)

    def verify_login(self, email: str, password: str) -> dict[str, Any] | None:
        conn = connect_mysql()
        try:
            sql = f"SELECT id, email, username, password_hash, is_admin FROM {quote_ident(self.table_name)} WHERE email = %s LIMIT 1"
            with conn.cursor() as cursor:
                cursor.execute(sql, (email,))
                user = cursor.fetchone()
            if not user:
                return None
            if int(user.get("is_admin") or 0) != 1:
                return None
            if not self.verify_password(password, user["password_hash"]):
                return None
            return {"id": user["id"], "email": user["email"], "username": user["username"], "is_admin": True}
        finally:
            conn.close()

    def create_admin(self, email: str, username: str, password: str) -> None:
        self.ensure_table()
        conn = connect_mysql()
        try:
            pwd_hash = self._hash_password(password)
            sql = f"""
            INSERT INTO {quote_ident(self.table_name)} (email, username, password_hash, is_admin)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                password_hash = VALUES(password_hash),
                is_admin = 1
            """
            with conn.cursor() as cursor:
                cursor.execute(sql, (email, username, pwd_hash))
        finally:
            conn.close()
