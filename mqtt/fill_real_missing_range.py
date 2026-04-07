import argparse
from datetime import datetime, timedelta

from backfill_real_history import (
    ZONES,
    connect_db,
    get_global_weather,
    get_zone_soil_data,
    quote_ident,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill missing rows in Real for a time range")
    parser.add_argument("--start", required=True, help="start timestamp, format: YYYY-mm-dd HH:MM:SS")
    parser.add_argument("--end", required=True, help="end timestamp (exclusive), format: YYYY-mm-dd HH:MM:SS")
    parser.add_argument("--table", default="Real", help="target table")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S")
    end_exclusive = datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
    table = args.table

    conn = connect_db()

    select_sql = f"""
    SELECT timestamp, zone_id
    FROM {quote_ident(table)}
    WHERE timestamp >= %s AND timestamp < %s
    """

    insert_sql = f"""
    INSERT INTO {quote_ident(table)} (
        timestamp, zone_id, air_temp, air_humidity, light_intensity,
        soil_temp, soil_humidity, ec, ph, n, p, k
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cursor:
        cursor.execute(select_sql, (start.strftime("%Y-%m-%d %H:%M:%S"), end_exclusive.strftime("%Y-%m-%d %H:%M:%S")))
        existing = {
            (row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), row["zone_id"])
            for row in cursor.fetchall()
        }

    rows = []
    ts = start
    while ts < end_exclusive:
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        air_temp, air_humidity, light = get_global_weather(ts)
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
        print("No missing rows in this range")

    conn.close()


if __name__ == "__main__":
    main()
