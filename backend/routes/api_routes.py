from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Request


class DifyAnalyzeRequest(BaseModel):
    file_name: str
    capture_time: str | None = None
    zone_id: str | None = None
    yolo_result: str | None = None
    confidence: int | None = None
    description: str | None = None


def build_api_router(
    data_service: Any,
    yolo_service: Any,
    dify_service: Any,
    output_dir: Path,
    valid_zones: list[str],
    metric_keys: list[str],
) -> APIRouter:
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

    @router.get("/yolo-detections")
    def api_yolo_detections(
        request: Request,
        limit: int = Query(5, ge=1, le=200),
        auto_refresh: bool = Query(False),
    ) -> dict[str, Any]:
        ensure_login(request)
        # For big-screen simulation, optionally rescan output images before reading latest rows.
        if auto_refresh:
            yolo_service.refresh_all()
        records = yolo_service.latest_detections(limit=limit)
        return {"records": records, "count": len(records)}

    @router.get("/yolo-annotated")
    def api_yolo_annotated(request: Request, file_name: str = Query(...)) -> dict[str, Any]:
        ensure_login(request)
        try:
            annotated = yolo_service.build_annotated_image(file_name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="annotated image source not found")
        return {"annotated_image_url": f"/annotated/{annotated.name}"}

    @router.post("/yolo-refresh")
    def api_yolo_refresh(request: Request, file_name: str | None = Query(default=None)) -> dict[str, Any]:
        ensure_login(request)
        if file_name:
            try:
                record = yolo_service.refresh_one(file_name)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="image not found in output directory")
            return {"mode": "single", "record": record}

        records = yolo_service.refresh_all()
        return {"mode": "all", "count": len(records)}

    @router.post("/dify/analyze-image")
    def api_dify_analyze_image(request: Request, body: DifyAnalyzeRequest) -> dict[str, Any]:
        ensure_login(request)
        if not dify_service.enabled:
            raise HTTPException(status_code=503, detail="dify api key not configured")

        image_path = output_dir / body.file_name
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail="image not found")

        try:
            annotated_image_path = yolo_service.build_annotated_image(body.file_name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        user = request.session.get("user") or "dashboard-user"
        prompt = (
            "你是一名植保专家，请根据这张YOLO带框图快速给出结论。"
            f"\n时间: {body.capture_time or '--'}"
            f"\n区域: {body.zone_id or '--'}"
            f"\nYOLO结果: {body.yolo_result or '--'}"
            f"\n置信度: {body.confidence if body.confidence is not None else '--'}%"
            f"\n补充说明: {body.description or '--'}"
            "\n请用中文直接输出，不要输出思考过程。"
            "\n格式：1) 病虫害判断 2) 严重程度 3) 用药/处置建议 4) 复查建议。"
        )
        try:
            result = dify_service.analyze_image(image_path=annotated_image_path, prompt=prompt, user=str(user))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="image not found")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"dify request failed: {exc}")

        return result

    @router.get("/yolo-placeholder")
    def api_yolo_placeholder(request: Request, limit: int = Query(4, ge=1, le=12)) -> dict[str, Any]:
        ensure_login(request)
        records = yolo_service.latest_detections(limit=limit)
        return {"records": records}

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
            "yolo_records": yolo_service.latest_detections(limit=5),
        }

    return router
