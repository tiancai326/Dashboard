import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from backend.services.db_utils import connect_mysql, db_lock, quote_ident


class DataService:
    def __init__(
        self,
        db_table: str,
        prediction_table: str,
        app_tz: str,
        legacy_real_tables: tuple[str, ...],
        valid_zones: list[str],
        metric_keys: list[str],
        gallery_dir: Path,
    ) -> None:
        self.db_table = db_table
        self.prediction_table = prediction_table
        self.app_tz = app_tz
        self.legacy_real_tables = legacy_real_tables
        self.valid_zones = valid_zones
        self.metric_keys = metric_keys
        self.gallery_dir = gallery_dir
        self.conn = None
        self.lock: threading.Lock = db_lock()

    def connect(self) -> None:
        self.conn = connect_mysql()

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _ensure_conn(self) -> None:
        if self.conn is None:
            raise RuntimeError("database is not connected")

    def table_exists(self, table_name: str) -> bool:
        self._ensure_conn()
        sql = """
        SELECT COUNT(1) AS c
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (table_name,))
                row = cursor.fetchone()
        return bool(row and row["c"] > 0)

    def ensure_real_table(self) -> None:
        self._ensure_conn()

        if not self.table_exists(self.db_table):
            for old_table in self.legacy_real_tables:
                if self.table_exists(old_table):
                    rename_sql = f"RENAME TABLE {quote_ident(old_table)} TO {quote_ident(self.db_table)}"
                    with self.lock:
                        with self.conn.cursor() as cursor:
                            cursor.execute(rename_sql)
                    break

        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quote_ident(self.db_table)} (
            id BIGINT NOT NULL AUTO_INCREMENT,
            timestamp DATETIME NOT NULL,
            zone_id VARCHAR(20) NOT NULL,
            air_temp FLOAT,
            air_humidity FLOAT,
            light_intensity INT,
            soil_temp FLOAT,
            soil_humidity FLOAT,
            ec FLOAT,
            ph FLOAT,
            n FLOAT,
            p FLOAT,
            k FLOAT,
            PRIMARY KEY (id),
            KEY idx_timestamp (timestamp),
            KEY idx_zone_id (zone_id),
            KEY idx_zone_timestamp (zone_id, timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(ddl)

    def insert_sensor_row(self, payload: dict[str, Any], zone_id: str) -> None:
        self._ensure_conn()
        now_local = datetime.now(ZoneInfo(self.app_tz))
        aligned = now_local.replace(minute=0, second=0, microsecond=0)

        sql = f"""
        INSERT INTO {quote_ident(self.db_table)} (
            timestamp, zone_id, air_temp, air_humidity, light_intensity,
            soil_temp, soil_humidity, ec, ph, n, p, k
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            aligned.strftime("%Y-%m-%d %H:%M:%S"),
            zone_id,
            payload.get("air_temp"),
            payload.get("air_humidity"),
            payload.get("light_intensity"),
            payload.get("soil_temp"),
            payload.get("soil_humidity"),
            payload.get("ec"),
            payload.get("ph"),
            payload.get("n"),
            payload.get("p"),
            payload.get("k"),
        )
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, values)

    def latest_zone_row(self, zone_id: str) -> dict[str, Any] | None:
        self._ensure_conn()
        sql = f"""
        SELECT timestamp, zone_id, air_temp, air_humidity, light_intensity,
               soil_temp, soil_humidity, ec, ph, n, p, k
        FROM {quote_ident(self.db_table)}
        WHERE zone_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (zone_id,))
                return cursor.fetchone()

    def latest_all_zone_rows(self) -> list[dict[str, Any]]:
        self._ensure_conn()
        sql = f"""
        SELECT r.zone_id, r.timestamp, r.soil_temp, r.soil_humidity, r.ec, r.air_temp, r.air_humidity
        FROM {quote_ident(self.db_table)} r
        JOIN (
            SELECT zone_id, MAX(timestamp) AS ts
            FROM {quote_ident(self.db_table)}
            GROUP BY zone_id
        ) t ON r.zone_id = t.zone_id AND r.timestamp = t.ts
        ORDER BY r.zone_id
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()

    def latest_predictions(self, zone_id: str, limit: int = 24) -> list[dict[str, Any]]:
        self._ensure_conn()
        if not self.table_exists(self.prediction_table):
            return []

        sql = f"""
        SELECT predict_time, zone_id, soil_temp_pred, soil_humidity_pred, ec_pred, weather_temp, weather_humidity
        FROM {quote_ident(self.prediction_table)}
        WHERE zone_id = %s
        ORDER BY predict_time DESC
        LIMIT %s
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (zone_id, limit))
                rows = cursor.fetchall()
        rows.reverse()
        return rows

    def build_zone_cards(self) -> list[dict[str, Any]]:
        latest_rows = {row["zone_id"]: row for row in self.latest_all_zone_rows()}
        cards = []
        for index, zone in enumerate(self.valid_zones, start=1):
            row = latest_rows.get(zone)
            cards.append(
                {
                    "zone_id": zone,
                    "label": f"区域 {index}",
                    "soil_humidity": row.get("soil_humidity") if row else None,
                    "ec": row.get("ec") if row else None,
                    "soil_temp": row.get("soil_temp") if row else None,
                    "air_temp": row.get("air_temp") if row else None,
                    "air_humidity": row.get("air_humidity") if row else None,
                    "timestamp": row.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if row else None,
                }
            )
        return cards

    def build_yolo_placeholder(self, limit: int = 4) -> list[dict[str, Any]]:
        if not self.gallery_dir.exists():
            return []

        image_files = sorted(
            [p for p in self.gallery_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        )
        records = []
        fallback_times = [
            "2026-04-06 10:22:15",
            "2026-04-06 10:31:09",
            "2026-04-06 10:44:28",
            "2026-04-06 10:56:02",
        ]
        fallback_zones = ["zone_3", "zone_2", "zone_5", "zone_1"]
        fallback_result = ["🟢 安全无虫害", "🟡 轻度虫害风险", "🟢 安全无虫害", "🟢 安全无虫害"]

        for i, path in enumerate(image_files[:limit]):
            records.append(
                {
                    "image_url": f"/gallery/{quote(path.name)}",
                    "capture_time": fallback_times[i % len(fallback_times)],
                    "zone_id": fallback_zones[i % len(fallback_zones)],
                    "result": fallback_result[i % len(fallback_result)],
                    "file_name": path.name,
                }
            )
        return records
