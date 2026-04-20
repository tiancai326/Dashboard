from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
ANNOTATED_DIR = ROOT_DIR / "backend" / "cache" / "annotated"
RESULT_FILE = ROOT_DIR / "backend" / "cache" / "yolo_detections.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def clear_folder(folder: Path, *, image_only: bool) -> int:
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        return 0

    removed = 0
    for item in folder.iterdir():
        if not item.is_file():
            continue
        if image_only and item.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        item.unlink(missing_ok=True)
        removed += 1
    return removed


def reset_result_file() -> None:
    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULT_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear all visual detection data")
    parser.add_argument(
        "--clear-output",
        action="store_true",
        help="Also clear original images under output/ (default is keep output originals)",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Deprecated compatibility flag. Output images are kept by default.",
    )
    args = parser.parse_args()

    removed_output = 0
    if args.clear_output:
        removed_output = clear_folder(OUTPUT_DIR, image_only=True)

    removed_annotated = clear_folder(ANNOTATED_DIR, image_only=True)
    reset_result_file()

    print("visual data cleared")
    print(f"output removed: {removed_output}")
    print(f"annotated removed: {removed_annotated}")
    print(f"index reset: {RESULT_FILE}")


if __name__ == "__main__":
    main()
