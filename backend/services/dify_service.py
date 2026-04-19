from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any

import requests
from requests.exceptions import ReadTimeout


class DifyService:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def _json_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _upload_file(self, image_path: Path, user: str) -> str:
        if not image_path.exists() or not image_path.is_file():
            raise FileNotFoundError(str(image_path))

        mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        with image_path.open("rb") as f:
            files = {
                "file": (image_path.name, f, mime),
            }
            data = {
                "user": user,
                "type": "image",
            }
            resp = requests.post(
                f"{self.base_url}/files/upload",
                headers=self._auth_headers(),
                files=files,
                data=data,
                timeout=self.timeout_seconds,
            )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"dify upload failed: {resp.status_code} {resp.text[:300]}")

        payload = resp.json()
        file_id = payload.get("id")
        if not file_id:
            raise RuntimeError("dify upload response missing file id")
        return str(file_id)

    def _fetch_parameters(self) -> dict[str, Any]:
        resp = requests.get(
            f"{self.base_url}/parameters",
            headers=self._auth_headers(),
            timeout=30,
        )
        if not resp.ok:
            return {}
        try:
            return resp.json()
        except Exception:
            return {}

    def _build_inputs(self, prompt: str, parameters: dict[str, Any], upload_file_id: str) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        file_bound = False
        for item in parameters.get("user_input_form", []):
            if not isinstance(item, dict):
                continue
            field_type = next(iter(item.keys()), "")
            field = next(iter(item.values()), {})
            if not isinstance(field, dict):
                continue
            var = field.get("variable")
            required = bool(field.get("required", False))
            default = field.get("default")
            if not var:
                continue

            if field_type == "file" or field.get("type") == "file":
                inputs[var] = {
                    "type": "image",
                    "transfer_method": "local_file",
                    "upload_file_id": upload_file_id,
                }
                file_bound = True
                continue

            if required:
                inputs[var] = prompt
            elif default not in (None, ""):
                inputs[var] = default

        # Fallback for common image variable naming in workflow apps.
        if not file_bound:
            inputs["image_file"] = {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": upload_file_id,
            }

        return inputs

    def analyze_image(self, image_path: Path, prompt: str, user: str) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("dify api key not configured")

        upload_file_id = self._upload_file(image_path=image_path, user=user)
        parameters = self._fetch_parameters()
        inputs = self._build_inputs(prompt=prompt, parameters=parameters, upload_file_id=upload_file_id)

        body = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/workflows/run",
                headers=self._json_headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
        except ReadTimeout:
            # Retry once for transient network or model queue delays.
            resp = requests.post(
                f"{self.base_url}/workflows/run",
                headers=self._json_headers(),
                json=body,
                timeout=self.timeout_seconds,
            )
        if not resp.ok:
            raise RuntimeError(f"dify workflow failed: {resp.status_code} {resp.text[:500]}")

        payload = resp.json()
        data = payload.get("data") or {}
        outputs = data.get("outputs") or {}

        text = ""
        if isinstance(outputs, dict):
            for value in outputs.values():
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break
        if not text:
            text = "Dify 已返回结果，但未识别到可展示的文本输出。"

        # Avoid showing chain-of-thought-like think blocks in UI.
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip() or text

        return {
            "workflow_run_id": payload.get("workflow_run_id"),
            "task_id": payload.get("task_id"),
            "status": data.get("status"),
            "text": text,
            "outputs": outputs,
        }
