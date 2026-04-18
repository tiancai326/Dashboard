import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote


class YoloService:
    def __init__(self, output_dir: Path, model_path: Path, valid_zones: list[str], result_file: Path) -> None:
        self.output_dir = output_dir
        self.model_path = model_path
        self.valid_zones = valid_zones
        self.result_file = result_file
        self._model = None
        self._model_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._cache: dict[tuple[str, int, int], dict[str, Any]] = {}

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model
            from ultralytics import YOLO

            self._model = YOLO(str(self.model_path))
        return self._model

    def _zone_from_filename(self, file_name: str) -> str:
        lowered = file_name.lower()
        for zone in self.valid_zones:
            if zone in lowered:
                return zone

        h = hashlib.md5(file_name.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16) % len(self.valid_zones)
        return self.valid_zones[idx]

    def _to_severity(self, label: str) -> str:
        text = label.lower()
        if any(k in text for k in ["healthy", "normal", "ok", "health", "健康"]):
            return "good"
        if any(k in text for k in ["severe", "serious", "rot", "moth", "worm", "虫", "病", "溃", "腐"]):
            return "danger"
        return "warn"

    def _severity_level(self, severity: str) -> str:
        if severity == "danger":
            return "严重虫害"
        if severity == "warn":
            return "轻度病害"
        return "果树健康"

    def _iter_images(self) -> list[Path]:
        if not self.output_dir.exists():
            return []
        images = [
            p
            for p in self.output_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        ]
        return sorted(images, key=lambda p: p.stat().st_mtime, reverse=True)

    def _read_results(self) -> list[dict[str, Any]]:
        if not self.result_file.exists():
            return []
        try:
            data = json.loads(self.result_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _write_results(self, records: list[dict[str, Any]]) -> None:
        self.result_file.parent.mkdir(parents=True, exist_ok=True)
        self.result_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_record(self, path: Path) -> dict[str, Any]:
        infer = self._infer_one(path)
        stat = path.stat()
        capture_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        zone_id = self._zone_from_filename(path.name)
        zone_text = zone_id.replace("zone_", "Zone_")

        if infer["detections"]:
            label_preview = ", ".join(sorted({d["label"] for d in infer["detections"]})[:3])
            desc = f"检测到 {len(infer['detections'])} 个目标，标签: {label_preview}"
        else:
            desc = "未检测到明显病虫害目标，叶片状态正常。"

        return {
            "id": f"{path.name}:{stat.st_mtime_ns}",
            "file_name": path.name,
            "image_url": f"/output/{quote(path.name)}",
            "capture_time": capture_time,
            "zone_id": zone_text,
            "summary_label": infer["summary_label"],
            "summary_confidence": infer["summary_confidence"],
            "severity": infer["severity"],
            "level_text": infer["level_text"],
            "description": desc,
            "detection_count": len(infer["detections"]),
            "image_width": infer["image_width"],
            "image_height": infer["image_height"],
            "detections": infer["detections"],
        }

    def _infer_one(self, image_path: Path) -> dict[str, Any]:
        stat = image_path.stat()
        cache_key = (str(image_path), stat.st_mtime_ns, stat.st_size)

        with self._cache_lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            model = self._load_model()
            results = model.predict(source=str(image_path), verbose=False)
            result = results[0]

            h, w = result.orig_shape
            names = result.names

            detections: list[dict[str, Any]] = []
            top = None
            for box in result.boxes:
                xyxy = [float(x) for x in box.xyxy[0].tolist()]
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                label = str(names.get(cls_id, cls_id))

                item = {
                    "label": label,
                    "confidence": conf,
                    "bbox": {
                        "x1": xyxy[0],
                        "y1": xyxy[1],
                        "x2": xyxy[2],
                        "y2": xyxy[3],
                    },
                }
                detections.append(item)
                if top is None or conf > top["confidence"]:
                    top = item
        except Exception:
            # Keep service available even when model dependencies are not ready.
            h, w = 0, 0
            detections = []
            top = None

        summary_label = top["label"] if top else "健康叶片"
        summary_conf = float(top["confidence"]) if top else 0.99
        severity = self._to_severity(summary_label)
        level = self._severity_level(severity)

        response = {
            "summary_label": summary_label,
            "summary_confidence": summary_conf,
            "severity": severity,
            "level_text": level,
            "image_width": int(w),
            "image_height": int(h),
            "detections": detections,
        }

        with self._cache_lock:
            self._cache[cache_key] = response
        return response

    def refresh_all(self) -> list[dict[str, Any]]:
        images = self._iter_images()
        if not images:
            self._write_results([])
            return []

        records: list[dict[str, Any]] = []
        for path in images:
            records.append(self._build_record(path))

        self._write_results(records)
        return records

    def refresh_one(self, file_name: str) -> dict[str, Any]:
        path = (self.output_dir / file_name).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(file_name)

        record = self._build_record(path)
        records = self._read_results()
        records = [r for r in records if str(r.get("file_name")) != file_name]
        records.append(record)
        records.sort(key=lambda r: str(r.get("capture_time", "")), reverse=True)
        self._write_results(records)
        return record

    def latest_detections(self, limit: int = 5) -> list[dict[str, Any]]:
        records = self._read_results()
        if not records:
            return []
        return records[:limit]
