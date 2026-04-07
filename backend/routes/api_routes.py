from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request


def build_api_router(data_service: Any, valid_zones: list[str], metric_keys: list[str]) -> APIRouter:
    router = APIRouter(prefix="/api")

    def normalize_zone(value: str) -> str:
        return value.strip().lower().replace("-", "_")

    def ensure_login(request: Request) -> None:
        if not request.session.get("user"):
            raise HTTPException(status_code=401, detail="not authenticated")

    @router.get("/zones")
    def api_zones(request: Request) -> dict[str, Any]:
        ensure_login(request)
        return {"zones": data_service.build_zone_cards()}

    @router.get("/latest")
    def api_latest(request: Request, zone_id: str = Query("zone_1")) -> dict[str, Any]:
        ensure_login(request)
        zone = normalize_zone(zone_id)
        if zone not in valid_zones:
            raise HTTPException(status_code=400, detail="invalid zone_id")

        row = data_service.latest_zone_row(zone)
        if row is None:
            raise HTTPException(status_code=404, detail="no sensor data")

        row["timestamp"] = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        return {
            "zone_id": zone,
            "timestamp": row["timestamp"],
            "metrics": {key: row.get(key) for key in metric_keys},
            "raw": row,
        }

    @router.get("/predictions")
    def api_predictions(
        request: Request,
        zone_id: str = Query("zone_1"),
        limit: int = Query(24, ge=1, le=72),
    ) -> dict[str, Any]:
        ensure_login(request)
        zone = normalize_zone(zone_id)
        if zone not in valid_zones:
            raise HTTPException(status_code=400, detail="invalid zone_id")

        rows = data_service.latest_predictions(zone, limit=limit)
        for row in rows:
            row["predict_time"] = row["predict_time"].strftime("%Y-%m-%d %H:%M:%S")

        return {"zone_id": zone, "count": len(rows), "rows": rows}

    @router.get("/yolo-placeholder")
    def api_yolo_placeholder(request: Request, limit: int = Query(4, ge=1, le=12)) -> dict[str, Any]:
        ensure_login(request)
        return {"records": data_service.build_yolo_placeholder(limit=limit)}

    @router.get("/overview")
    def api_overview(request: Request, zone_id: str = Query("zone_1")) -> dict[str, Any]:
        ensure_login(request)
        zone = normalize_zone(zone_id)
        if zone not in valid_zones:
            raise HTTPException(status_code=400, detail="invalid zone_id")

        latest_row = data_service.latest_zone_row(zone)
        latest_payload = None
        if latest_row:
            latest_payload = {
                "timestamp": latest_row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "metrics": {key: latest_row.get(key) for key in metric_keys},
            }

        prediction_rows = data_service.latest_predictions(zone, limit=24)
        for row in prediction_rows:
            row["predict_time"] = row["predict_time"].strftime("%Y-%m-%d %H:%M:%S")

        return {
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "zone_id": zone,
            "zones": data_service.build_zone_cards(),
            "latest": latest_payload,
            "predictions": prediction_rows,
            "yolo_records": data_service.build_yolo_placeholder(limit=4),
        }

    return router
