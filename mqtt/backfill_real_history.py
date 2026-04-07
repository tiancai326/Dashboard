import math
import os
import random
from datetime import datetime, timedelta

import pymysql

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "xL4noaDNexXCSseoqWHE")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_TABLE = os.getenv("DB_TABLE", "Real")
DB_SOCKET = os.getenv("DB_SOCKET", "/var/run/mysqld/mysqld.sock")

ZONES = [f"zone_{i}" for i in range(1, 7)]
START = datetime(2026, 4, 1, 0, 0, 0)
END_EXCLUSIVE = datetime(2026, 4, 4, 21, 0, 0)


def quote_ident(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def connect_db() -> pymysql.Connection:
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


def get_global_weather(ts: datetime) -> tuple[float, float, int]:
    current_hour = ts.hour
    is_daytime = 6 <= current_hour <= 18

    if is_daytime:
        air_temp = round(random.uniform(25.0, 32.0), 1)
        air_humidity = round(random.uniform(60.0, 75.0), 1)

        time_fraction = (current_hour - 6) / 12.0
        peak_light = random.uniform(80000, 100000)
        light = int(peak_light * math.sin(time_fraction * math.pi))
        if random.random() < 0.2:
            light = int(light * 0.6)
    else:
        air_temp = round(random.uniform(15.0, 22.0), 1)
        air_humidity = round(random.uniform(75.0, 95.0), 1)
        light = 0

    return air_temp, air_humidity, light


def get_zone_soil_data() -> tuple[float, float, float, float, float, float, float]:
    soil_humidity = round(random.uniform(60.0, 80.0), 1)
    soil_temp = round(random.uniform(17.0, 26.0), 1)
    ec = round(random.uniform(0.5, 1.5), 2)
    ph = round(random.uniform(5.5, 6.5), 1)
    n = round(random.uniform(80, 150), 1)
    p = round(random.uniform(30, 40), 1)
    k = round(random.uniform(100, 250), 1)

    anomaly_chance = random.random()
    if anomaly_chance < 0.04:
        soil_humidity = round(random.uniform(30.0, 45.0), 1)
    elif 0.04 <= anomaly_chance < 0.08:
        soil_humidity = round(random.uniform(85.0, 95.0), 1)
        ec = round(random.uniform(0.1, 0.3), 2)
        n = round(random.uniform(10.0, 39.0), 1)
        p = round(random.uniform(5.0, 14.0), 1)
        k = round(random.uniform(10.0, 49.0), 1)
    elif 0.08 <= anomaly_chance < 0.12:
        ec = round(random.uniform(2.0, 3.5), 2)
        n = round(random.uniform(251.0, 400.0), 1)
        p = round(random.uniform(81.0, 150.0), 1)
        k = round(random.uniform(401.0, 600.0), 1)
    elif 0.12 <= anomaly_chance < 0.15:
        soil_temp = round(random.uniform(32.0, 36.0), 1)

    return soil_temp, soil_humidity, n, p, k, ph, ec


def main() -> None:
    random.seed(20260404)
    conn = connect_db()

    select_sql = f"""
    SELECT timestamp, zone_id
    FROM {quote_ident(DB_TABLE)}
    WHERE timestamp >= %s AND timestamp < %s
    """

    insert_sql = f"""
    INSERT INTO {quote_ident(DB_TABLE)} (
        timestamp, zone_id, air_temp, air_humidity, light_intensity,
        soil_temp, soil_humidity, ec, ph, n, p, k
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cursor:
        cursor.execute(select_sql, (START.strftime("%Y-%m-%d %H:%M:%S"), END_EXCLUSIVE.strftime("%Y-%m-%d %H:%M:%S")))
        existing = {
            (row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), row["zone_id"])
            for row in cursor.fetchall()
        }

    rows: list[tuple] = []
    ts = START
    while ts < END_EXCLUSIVE:
        air_temp, air_humidity, light = get_global_weather(ts)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        for zone in ZONES:
            key = (ts_str, zone)
            if key in existing:
                continue
            soil_temp, soil_humidity, n, p, k, ph, ec = get_zone_soil_data()
            rows.append(
                (
                    ts_str,
                    zone,
                    air_temp,
                    air_humidity,
                    light,
                    soil_temp,
                    soil_humidity,
                    ec,
                    ph,
                    n,
                    p,
                    k,
                )
            )

        ts += timedelta(hours=1)

    if rows:
        with conn.cursor() as cursor:
            cursor.executemany(insert_sql, rows)
        print(f"Inserted rows: {len(rows)}")
    else:
        print("No rows inserted, target range already complete")

    conn.close()


if __name__ == "__main__":
    main()
