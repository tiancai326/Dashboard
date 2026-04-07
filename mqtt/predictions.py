import argparse
import logging
import os
import pickle
import threading
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pymysql
import requests
import torch
import torch.nn as nn

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("dashboard-predictor")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "xL4noaDNexXCSseoqWHE")
DB_NAME = os.getenv("DB_NAME", "app_db")
REAL_TABLE = os.getenv("DB_TABLE", "Real")
PREDICTION_TABLE = os.getenv("PREDICTION_TABLE", "predictions")
DB_SOCKET = os.getenv("DB_SOCKET", "/var/run/mysqld/mysqld.sock")
APP_TZ = os.getenv("APP_TZ", "Asia/Shanghai")

WEATHER_API_HOST = os.getenv("WEATHER_API_HOST", "nh6r6wdwq5.re.qweatherapi.com")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "2d02df07249c49a190b28d7316ec8f0f")
WEATHER_LOCATION = os.getenv("WEATHER_LOCATION", "110.2818122,21.6121954")

MODEL_BASE_DIR = os.getenv("MODEL_BASE_DIR", "/root/Dashboard/best_model&scaler")
MODEL_PATH = os.path.join(MODEL_BASE_DIR, "best_model.pth")
X1_SCALER_PATH = os.path.join(MODEL_BASE_DIR, "x1_scaler.pkl")
X2_SCALER_PATH = os.path.join(MODEL_BASE_DIR, "x2_scaler.pkl")
Y_SCALER_PATH = os.path.join(MODEL_BASE_DIR, "y_scaler.pkl")

VALID_ZONES = [f"zone_{i}" for i in range(1, 7)]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def quote_ident(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def align_to_hour(ts: datetime) -> datetime:
    return ts.replace(minute=0, second=0, microsecond=0)


def seconds_until_next_hour(now: datetime) -> float:
    elapsed = now.minute * 60 + now.second + now.microsecond / 1_000_000
    wait = 3600 - elapsed
    return 0 if wait < 0.001 else wait


class EncoderDecoderLSTM(nn.Module):
    def __init__(
        self,
        encoder_input_dim: int = 5,
        decoder_input_dim: int = 2,
        hidden_dim: int = 128,
        num_layers: int = 2,
        output_dim: int = 3,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.encoder_lstm = nn.LSTM(
            input_size=encoder_input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.decoder_lstm = nn.LSTM(
            input_size=decoder_input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim),
        )

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        _, (hidden, cell) = self.encoder_lstm(x1)
        decoder_output, _ = self.decoder_lstm(x2, (hidden, cell))
        return self.fc(decoder_output)


class DBClient:
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
            return
        self.conn = pymysql.connect(host=DB_HOST, port=DB_PORT, **common)

    def ensure_prediction_table(self) -> None:
        if self.conn is None:
            raise RuntimeError("database is not connected")
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quote_ident(PREDICTION_TABLE)} (
            id BIGINT NOT NULL AUTO_INCREMENT,
            predict_time DATETIME NOT NULL,
            zone_id VARCHAR(20) NOT NULL,
            soil_temp_pred FLOAT NOT NULL,
            soil_humidity_pred FLOAT NOT NULL,
            ec_pred FLOAT NOT NULL,
            weather_temp FLOAT,
            weather_humidity FLOAT,
            PRIMARY KEY (id),
            KEY idx_predict_time (predict_time),
            UNIQUE KEY uk_zone_predict_time (zone_id, predict_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(ddl)

    def fetch_last_72h(self, zone_id: str) -> list[dict[str, Any]]:
        if self.conn is None:
            raise RuntimeError("database is not connected")
        sql = f"""
        SELECT timestamp, air_temp, air_humidity, soil_temp, soil_humidity, ec
        FROM {quote_ident(REAL_TABLE)}
        WHERE zone_id = %s
        ORDER BY timestamp DESC
        LIMIT 72
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, (zone_id,))
                rows = cursor.fetchall()
        rows.reverse()
        return rows

    def insert_predictions(self, rows: list[tuple[Any, ...]]) -> None:
        if self.conn is None:
            raise RuntimeError("database is not connected")
        if not rows:
            return
        sql = f"""
        INSERT INTO {quote_ident(PREDICTION_TABLE)} (
            predict_time, zone_id,
            soil_temp_pred, soil_humidity_pred, ec_pred,
            weather_temp, weather_humidity
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            soil_temp_pred = VALUES(soil_temp_pred),
            soil_humidity_pred = VALUES(soil_humidity_pred),
            ec_pred = VALUES(ec_pred),
            weather_temp = VALUES(weather_temp),
            weather_humidity = VALUES(weather_humidity)
        """
        with self.lock:
            with self.conn.cursor() as cursor:
                cursor.executemany(sql, rows)


class Predictor:
    def __init__(self) -> None:
        self.model: EncoderDecoderLSTM | None = None
        self.x1_scaler = None
        self.x2_scaler = None
        self.y_scaler = None

    def load(self) -> None:
        with open(X1_SCALER_PATH, "rb") as f:
            self.x1_scaler = pickle.load(f)
        with open(X2_SCALER_PATH, "rb") as f:
            self.x2_scaler = pickle.load(f)
        with open(Y_SCALER_PATH, "rb") as f:
            self.y_scaler = pickle.load(f)

        model = EncoderDecoderLSTM().to(DEVICE)
        state = torch.load(MODEL_PATH, map_location=DEVICE)
        model.load_state_dict(state)
        model.eval()
        self.model = model

    def predict(self, x1_raw: np.ndarray, x2_raw: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("predictor not loaded")
        x1_norm = self.x1_scaler.transform(x1_raw)
        x2_norm = self.x2_scaler.transform(x2_raw)

        x1 = torch.FloatTensor(x1_norm).unsqueeze(0).to(DEVICE)
        x2 = torch.FloatTensor(x2_norm).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            output = self.model(x1, x2).cpu().numpy()[0]
        return self.y_scaler.inverse_transform(output)


def fetch_weather_24h() -> tuple[list[datetime], np.ndarray]:
    host = WEATHER_API_HOST if WEATHER_API_HOST.startswith("http") else f"https://{WEATHER_API_HOST}"
    url = f"{host}/v7/weather/24h"

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {WEATHER_API_KEY}"},
        params={"location": WEATHER_LOCATION},
        timeout=20,
    )
    if response.status_code == 401:
        response = requests.get(
            url,
            params={"location": WEATHER_LOCATION, "key": WEATHER_API_KEY},
            timeout=20,
        )

    response.raise_for_status()
    data = response.json()
    if data.get("code") != "200":
        raise RuntimeError(f"weather api error: {data.get('code')}")

    hourly = data.get("hourly", [])[:24]
    if len(hourly) < 24:
        raise RuntimeError("weather api hourly data less than 24")

    times: list[datetime] = []
    x2 = np.zeros((24, 2), dtype=np.float32)
    for i, item in enumerate(hourly):
        dt = datetime.fromisoformat(item["fxTime"])
        dt = align_to_hour(dt.astimezone(ZoneInfo(APP_TZ)).replace(tzinfo=None))
        times.append(dt)
        x2[i, 0] = float(item["temp"])
        x2[i, 1] = float(item["humidity"])

    return times, x2


def run_prediction_once(db: DBClient, predictor: Predictor, run_at: datetime | None = None) -> int:
    forecast_times, x2 = fetch_weather_24h()
    if run_at is None:
        base_hour = align_to_hour(datetime.now(ZoneInfo(APP_TZ)).replace(tzinfo=None))
    else:
        base_hour = align_to_hour(run_at)

    predict_times = [base_hour + timedelta(hours=i + 1) for i in range(24)]

    rows_to_insert: list[tuple[Any, ...]] = []
    for zone_id in VALID_ZONES:
        rows = db.fetch_last_72h(zone_id)
        if len(rows) < 72:
            logger.warning("Skip prediction for %s: only %d rows in Real", zone_id, len(rows))
            continue

        x1 = np.array(
            [[r["air_temp"], r["air_humidity"], r["soil_temp"], r["soil_humidity"], r["ec"]] for r in rows],
            dtype=np.float32,
        )
        y_pred = predictor.predict(x1, x2)

        for i in range(24):
            rows_to_insert.append(
                (
                    predict_times[i].strftime("%Y-%m-%d %H:%M:%S"),
                    zone_id,
                    float(y_pred[i, 0]),
                    float(y_pred[i, 1]),
                    float(y_pred[i, 2]),
                    float(x2[i, 0]),
                    float(x2[i, 1]),
                )
            )

    db.insert_predictions(rows_to_insert)
    logger.info("Prediction job finished, inserted rows=%d", len(rows_to_insert))
    return len(rows_to_insert)


def run_scheduler(db: DBClient, predictor: Predictor) -> None:
    while True:
        now = datetime.now(ZoneInfo(APP_TZ))
        wait = seconds_until_next_hour(now)
        if wait > 0:
            logger.info("Waiting %.1f seconds for next top-of-hour", wait)
            time.sleep(wait)
        try:
            run_prediction_once(db, predictor)
        except Exception as exc:
            logger.exception("Prediction loop failed: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prediction worker")
    parser.add_argument("--once", action="store_true", help="run one prediction job then exit")
    parser.add_argument("--run-at", type=str, default="", help="simulate run hour, format: YYYY-mm-dd HH:MM:SS")
    args = parser.parse_args()

    db = DBClient()
    db.connect()
    db.ensure_prediction_table()

    predictor = Predictor()
    predictor.load()

    run_at = None
    if args.run_at:
        run_at = datetime.strptime(args.run_at, "%Y-%m-%d %H:%M:%S")

    if args.once:
        run_prediction_once(db, predictor, run_at=run_at)
        return

    run_scheduler(db, predictor)


if __name__ == "__main__":
    main()
