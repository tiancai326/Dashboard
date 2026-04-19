import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.routes.api_routes import build_api_router
from backend.routes.auth_routes import build_auth_router
from backend.routes.basic_routes import build_basic_router
from backend.services.auth_service import AuthService
from backend.services.data_service import DataService
from backend.services.dify_service import DifyService
from backend.services.mqtt_service import MqttIngestService
from backend.services.yolo_service import YoloService

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("dashboard-backend")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
GALLERY_DIR = BASE_DIR / "图集"
OUTPUT_DIR = BASE_DIR / "output"
YOLO_MODEL_PATH = BASE_DIR / "yolo" / "best.pt"
YOLO_RESULT_FILE = BASE_DIR / "backend" / "cache" / "yolo_detections.json"
ANNOTATED_DIR = BASE_DIR / "backend" / "cache" / "annotated"
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "orchard/sensor/")
MQTT_VALVE_ACK_TOPIC = os.getenv("MQTT_VALVE_ACK_TOPIC", "orchard/ack/zone1")

DB_TABLE = os.getenv("DB_TABLE", "Real")
PREDICTION_TABLE = os.getenv("PREDICTION_TABLE", "predictions")
APP_TZ = os.getenv("APP_TZ", "Asia/Shanghai")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "http://1.14.148.230/v1")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "app-8FhQNOqmvlep6zfDqcyrM4Fn")
DIFY_TIMEOUT_SECONDS = int(os.getenv("DIFY_TIMEOUT_SECONDS", "300"))

SESSION_SECRET = os.getenv("SESSION_SECRET", "replace-this-session-secret")

LEGACY_REAL_TABLES = ("mqttz_test", "mqtt_test")
VALID_ZONES = [f"zone_{i}" for i in range(1, 7)]
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

app = FastAPI(title="Dashboard Backend")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60 * 60 * 12, same_site="lax")

if WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")
if GALLERY_DIR.exists():
    app.mount("/gallery", StaticFiles(directory=str(GALLERY_DIR)), name="gallery")
if OUTPUT_DIR.exists():
    app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/annotated", StaticFiles(directory=str(ANNOTATED_DIR)), name="annotated")


data_service = DataService(
    db_table=DB_TABLE,
    prediction_table=PREDICTION_TABLE,
    app_tz=APP_TZ,
    legacy_real_tables=LEGACY_REAL_TABLES,
    valid_zones=VALID_ZONES,
    metric_keys=METRIC_KEYS,
    gallery_dir=GALLERY_DIR,
)
auth_service = AuthService()
mqtt_service = MqttIngestService(
    data_service=data_service,
    valid_zones=VALID_ZONES,
    topic_prefix=MQTT_TOPIC_PREFIX,
    valve_ack_topic=MQTT_VALVE_ACK_TOPIC,
    broker=MQTT_BROKER,
    port=MQTT_PORT,
)
yolo_service = YoloService(
    output_dir=OUTPUT_DIR,
    model_path=YOLO_MODEL_PATH,
    valid_zones=VALID_ZONES,
    result_file=YOLO_RESULT_FILE,
)
dify_service = DifyService(base_url=DIFY_BASE_URL, api_key=DIFY_API_KEY, timeout_seconds=DIFY_TIMEOUT_SECONDS)

app.include_router(build_auth_router(WEB_DIR, auth_service))
app.include_router(build_basic_router(WEB_DIR))
app.include_router(build_api_router(data_service, yolo_service, dify_service, OUTPUT_DIR, VALID_ZONES, METRIC_KEYS))


@app.on_event("startup")
def startup() -> None:
    data_service.connect()
    data_service.ensure_real_table()
    auth_service.ensure_table()
    mqtt_service.start()
    try:
        yolo_service.refresh_all()
    except Exception as exc:
        logger.exception("YOLO initial refresh failed: %s", exc)
    logger.info("Backend service started")


@app.on_event("shutdown")
def shutdown() -> None:
    mqtt_service.stop()
    data_service.close()
    logger.info("Backend service stopped")
