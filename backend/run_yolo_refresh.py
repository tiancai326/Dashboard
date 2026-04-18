from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.yolo_service import YoloService


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh YOLO detections from output images")
    parser.add_argument("--file", dest="file_name", help="Image file name already under output/, e.g. p17_or.jpg")
    parser.add_argument("--source", help="Local image path to copy into output/ and then detect")
    parser.add_argument("--all", action="store_true", help="Refresh all images in output/")
    args = parser.parse_args()

    base_dir = ROOT_DIR
    output_dir = base_dir / "output"
    model_path = base_dir / "yolo" / "best.pt"
    result_file = base_dir / "backend" / "cache" / "yolo_detections.json"
    valid_zones = [f"zone_{i}" for i in range(1, 7)]

    output_dir.mkdir(parents=True, exist_ok=True)

    svc = YoloService(
        output_dir=output_dir,
        model_path=model_path,
        valid_zones=valid_zones,
        result_file=result_file,
    )

    if args.source:
        src = Path(args.source).expanduser().resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"source image not found: {src}")
        target = output_dir / src.name
        shutil.copy2(src, target)
        record = svc.refresh_one(src.name)
        print(f"single refreshed: {record['file_name']} -> {record['summary_label']} ({record['detection_count']} boxes)")
        return

    if args.file_name:
        record = svc.refresh_one(args.file_name)
        print(f"single refreshed: {record['file_name']} -> {record['summary_label']} ({record['detection_count']} boxes)")
        return

    if args.all or (not args.file_name and not args.source):
        records = svc.refresh_all()
        print(f"all refreshed: {len(records)} image(s)")
        return


if __name__ == "__main__":
    main()
