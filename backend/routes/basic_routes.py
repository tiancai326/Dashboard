from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse


def build_basic_router(web_dir: Path) -> APIRouter:
    router = APIRouter()

    def ensure_login(request: Request):
        if not request.session.get("user"):
            return RedirectResponse(url="/login", status_code=302)
        return None

    @router.get("/")
    def index(request: Request):
        denied = ensure_login(request)
        if denied:
            return denied
        page = web_dir / "index.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
        return FileResponse(page)

    @router.get("/admin")
    def admin_page(request: Request):
        denied = ensure_login(request)
        if denied:
            return denied
        page = web_dir / "admin.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="admin.html not found")
        return FileResponse(page)

    @router.get("/diagnosis")
    def diagnosis_page(request: Request):
        denied = ensure_login(request)
        if denied:
            return denied
        page = web_dir / "diagnosis.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="diagnosis.html not found")
        return FileResponse(page)

    @router.get("/yolo")
    def yolo_page(request: Request):
        denied = ensure_login(request)
        if denied:
            return denied
        page = web_dir / "yolo.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="yolo.html not found")
        return FileResponse(page)

    @router.get("/valve")
    def valve_page(request: Request):
        denied = ensure_login(request)
        if denied:
            return denied
        page = web_dir / "valve.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="valve.html not found")
        return FileResponse(page)

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "backend-ingest"}

    return router
