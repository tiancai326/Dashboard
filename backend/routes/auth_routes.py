from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel


class LoginPayload(BaseModel):
    email: str
    password: str


def build_auth_router(web_dir: Path, auth_service: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/login")
    def login_page(request: Request):
        if request.session.get("user"):
            return RedirectResponse(url="/", status_code=302)
        page = web_dir / "login.html"
        if not page.exists():
            raise HTTPException(status_code=404, detail="login.html not found")
        return FileResponse(page)

    @router.post("/auth/login")
    def login(payload: LoginPayload, request: Request) -> dict[str, Any]:
        user = auth_service.verify_login(payload.email.strip().lower(), payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        request.session["user"] = user
        return {"ok": True, "redirect": "/", "user": {"email": user["email"], "username": user["username"]}}

    @router.post("/auth/logout")
    def logout(request: Request) -> dict[str, Any]:
        request.session.clear()
        return {"ok": True, "redirect": "/login"}

    return router
