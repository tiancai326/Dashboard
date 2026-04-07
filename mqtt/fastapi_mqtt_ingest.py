import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt
import pymysql
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("dashboard-mqtt-ingest")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
GALLERY_DIR = BASE_DIR / "图集"

app = FastAPI(title="Dashboard MQTT Ingest")

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "orchard/sensor/")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "xL4noaDNexXCSseoqWHE")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_TABLE = os.getenv("DB_TABLE", "Real")
PREDICTION_TABLE = os.getenv("PREDICTION_TABLE", "predictions")
DB_SOCKET = os.getenv("DB_SOCKET", "/var/run/mysqld/mysqld.sock")
APP_TZ = os.getenv("APP_TZ", "Asia/Shanghai")

LEGACY_REAL_TABLES = ("mqttz_test", "mqtt_test")
VALID_ZONES = [f"zone_{i}" for i in range(1, 7)]
SUB_TOPICS = [(f"{MQTT_TOPIC_PREFIX}{zone}", 0) for zone in VALID_ZONES]
SUB_TOPICS += [(f"{MQTT_TOPIC_PREFIX}Zone_{i}", 0) for i in range(1, 7)]

METRIC_KEYS = [
    "air_temp",
    "air_humidity",
    "light_intensity",
    "soil_temp",
    "soil_humidity",
    "ec",
    "ph",
    "n",
    "p",
    "k",
]

if WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")
if GALLERY_DIR.exists():
    app.mount("/gallery", StaticFiles(directory=str(GALLERY_DIR)), name="gallery")


def quote_ident(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def align_to_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def normalize_zone(value: str) -> str:
    return value.strip().lower().replace("-", "_")


class DBWriter:
    def __init__(self) -> None:
        self.conn: pymysql.Connection | None = None
        self.lock = threading.Lock()

    def connect(self) -> None:
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
            self.conn = pymysql.connect(unix_socket=DB_SOCKET, **common)
            logger.info("MySQL connected via unix socket: %s", DB_SOCKET)
            return

        self.conn = pymysql.connect(host=DB_HOST, port=DB_PORT, **common)
        logger.info("MySQL connected via TCP: %s:%s", DB_HOST, DB_PORT)

    def table_exists(self, table_name: str) -> bool:
        if self.conn is None:
            raise RuntimeError("database is not connected")
        sql = """
        SELECT COUNT(1) AS c
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (DB_NAME, table_name))
                row = cursor.fetchone()
        return bool(row and row["c"] > 0)

    def ensure_real_table(self) -> None:
        if self.conn is None:
            raise RuntimeError("database is not connected")

        if not self.table_exists(DB_TABLE):
            for old_table in LEGACY_REAL_TABLES:
                if self.table_exists(old_table):
                    rename_sql = f"RENAME TABLE {quote_ident(old_table)} TO {quote_ident(DB_TABLE)}"
                    with self.lock:
                        with self.conn.cursor() as cursor:
                            cursor.execute(rename_sql)
                    logger.info("Renamed legacy table %s to %s", old_table, DB_TABLE)
                    break

        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quote_ident(DB_TABLE)} (
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
        if self.conn is None:
            raise RuntimeError("database is not connected")

        local_now = datetime.now(ZoneInfo(APP_TZ))
        aligned_hour = align_to_hour(local_now)

        sql = f"""
        INSERT INTO {quote_ident(DB_TABLE)} (
            timestamp, zone_id, air_temp, air_humidity, light_intensity,
            soil_temp, soil_humidity, ec, ph, n, p, k
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            aligned_hour.strftime("%Y-%m-%d %H:%M:%S"),
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
        if self.conn is None:
            raise RuntimeError("database is not connected")

        sql = f"""
        SELECT timestamp, zone_id, air_temp, air_humidity, light_intensity,
               soil_temp, soil_humidity, ec, ph, n, p, k
        FROM {quote_ident(DB_TABLE)}
        WHERE zone_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (zone_id,))
                return cursor.fetchone()

    def latest_all_zone_rows(self) -> list[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("database is not connected")

        sql = f"""
        SELECT r.zone_id, r.timestamp, r.soil_temp, r.soil_humidity, r.ec, r.air_temp, r.air_humidity
        FROM {quote_ident(DB_TABLE)} r
        JOIN (
            SELECT zone_id, MAX(timestamp) AS ts
            FROM {quote_ident(DB_TABLE)}
            GROUP BY zone_id
        ) t ON r.zone_id = t.zone_id AND r.timestamp = t.ts
        ORDER BY r.zone_id
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()

    def latest_predictions(self, zone_id: str, limit: int = 24) -> list[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("database is not connected")
        if not self.table_exists(PREDICTION_TABLE):
            return []

        sql = f"""
        SELECT predict_time, zone_id, soil_temp_pred, soil_humidity_pred, ec_pred, weather_temp, weather_humidity
        FROM {quote_ident(PREDICTION_TABLE)}
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


writer = DBWriter()
mqtt_client: mqtt.Client | None = None
mqtt_started = threading.Event()


def resolve_zone(msg_topic: str, payload: dict[str, Any]) -> str | None:
    topic_zone = normalize_zone(msg_topic.split("/")[-1])
    payload_zone = normalize_zone(str(payload.get("zone_id", "")))
    if topic_zone in VALID_ZONES:
        return topic_zone
    if payload_zone in VALID_ZONES:
        return payload_zone
    return None


def on_connect(client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
    if rc != 0:
        logger.error("MQTT connect failed. rc=%s", rc)
        return
    client.subscribe(SUB_TOPICS)
    logger.info("MQTT connected and subscribed: %s", [t[0] for t in SUB_TOPICS])


def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as exc:
        logger.error("Invalid JSON from %s: %s", msg.topic, exc)
        return

    zone_id = resolve_zone(msg.topic, payload)
    if zone_id is None:
        logger.warning("Skip unknown zone. topic=%s payload=%s", msg.topic, payload)
        return

    try:
        writer.insert_sensor_row(payload, zone_id)
        logger.info("Inserted sensor row: topic=%s zone_id=%s", msg.topic, zone_id)
    except Exception as exc:
        logger.exception("Insert failed: %s", exc)


def start_mqtt() -> None:
    global mqtt_client
    if mqtt_started.is_set():
        return

    mqtt_client = mqtt.Client(client_id=f"dashboard_ingest_{os.getpid()}", protocol=mqtt.MQTTv311)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    mqtt_started.set()


def build_zone_cards() -> list[dict[str, Any]]:
    latest_rows = {row["zone_id"]: row for row in writer.latest_all_zone_rows()}
    cards = []
    for index, zone in enumerate(VALID_ZONES, start=1):
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


def build_yolo_placeholder(limit: int = 4) -> list[dict[str, Any]]:
    if not GALLERY_DIR.exists():
        return []

    image_files = sorted(
        [p for p in GALLERY_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
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


@app.on_event("startup")
def startup() -> None:
    writer.connect()
    writer.ensure_real_table()
    start_mqtt()
    logger.info("FastAPI MQTT ingest service started.")


@app.on_event("shutdown")
def shutdown() -> None:
    if mqtt_client is not None:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if writer.conn is not None:
        writer.conn.close()
    logger.info("FastAPI MQTT ingest service stopped.")


@app.get("/")
def index() -> FileResponse:
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.get("/admin")
def admin_page() -> FileResponse:
    admin_file = WEB_DIR / "admin.html"
    if not admin_file.exists():
        raise HTTPException(status_code=404, detail="admin.html not found")
    return FileResponse(admin_file)


@app.get("/diagnosis")
def diagnosis_page() -> FileResponse:
    diagnosis_file = WEB_DIR / "diagnosis.html"
    if not diagnosis_file.exists():
        raise HTTPException(status_code=404, detail="diagnosis.html not found")
    return FileResponse(diagnosis_file)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "mqtt-ingest"}


@app.get("/api/zones")
def api_zones() -> dict[str, Any]:
    return {"zones": build_zone_cards()}


@app.get("/api/latest")
def api_latest(zone_id: str = Query("zone_1")) -> dict[str, Any]:
    zone = normalize_zone(zone_id)
    if zone not in VALID_ZONES:
        raise HTTPException(status_code=400, detail="invalid zone_id")

    row = writer.latest_zone_row(zone)
    if row is None:
        raise HTTPException(status_code=404, detail="no sensor data")

    row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return {
        "zone_id": zone,
        "timestamp": row["timestamp"],
        "metrics": {key: row.get(key) for key in METRIC_KEYS},
        "raw": row,
    }


@app.get("/api/predictions")
def api_predictions(
    zone_id: str = Query("zone_1"),
    limit: int = Query(24, ge=1, le=72),
) -> dict[str, Any]:
    zone = normalize_zone(zone_id)
    if zone not in VALID_ZONES:
        raise HTTPException(status_code=400, detail="invalid zone_id")

    rows = writer.latest_predictions(zone, limit=limit)
    for row in rows:
        row["predict_time"] = row["predict_time"].strftime("%Y-%m-%d %H:%M:%S")

    return {
        "zone_id": zone,
        "count": len(rows),
        "rows": rows,
    }


@app.get("/api/yolo-placeholder")
def api_yolo_placeholder(limit: int = Query(4, ge=1, le=12)) -> dict[str, Any]:
    return {"records": build_yolo_placeholder(limit=limit)}


@app.get("/api/overview")
def api_overview(zone_id: str = Query("zone_1")) -> dict[str, Any]:
    zone = normalize_zone(zone_id)
    if zone not in VALID_ZONES:
        raise HTTPException(status_code=400, detail="invalid zone_id")

    latest_row = writer.latest_zone_row(zone)
    latest_payload = None
    if latest_row:
        latest_payload = {
            "timestamp": latest_row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {key: latest_row.get(key) for key in METRIC_KEYS},
        }

    prediction_rows = writer.latest_predictions(zone, limit=24)
    for row in prediction_rows:
        row["predict_time"] = row["predict_time"].strftime("%Y-%m-%d %H:%M:%S")

    now_local = datetime.now(ZoneInfo(APP_TZ))
    return {
        "now": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "zone_id": zone,
        "zones": build_zone_cards(),
        "latest": latest_payload,
        "predictions": prediction_rows,
        "yolo_records": build_yolo_placeholder(limit=4),
    }
