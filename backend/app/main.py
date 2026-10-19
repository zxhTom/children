from collections import defaultdict
from pathlib import Path
from time import monotonic
import os
import uuid

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth
from .api import router
from .migrations import initialize_database


initialize_database()

app = FastAPI(title="家庭时光机 API")
PASSWORD_HASH, AUTH_SECRET = auth.configuration()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
login_attempts = defaultdict(list)


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    public = path in ("/login", "/api/login")
    if not public and not auth.valid_session(request.cookies.get(auth.COOKIE_NAME), AUTH_SECRET):
        if path.startswith("/api/") or path.startswith("/static_uploads/"):
            return JSONResponse({"detail": "请先登录"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
            return JSONResponse({"detail": "请求来源无效"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if path.startswith("/api/") or path in ("/", "/login"):
        response.headers["Cache-Control"] = "no-store"
    return response


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/login")
def login_page(request: Request):
    if auth.valid_session(request.cookies.get(auth.COOKIE_NAME), AUTH_SECRET):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "login.html")


@app.post("/api/login")
def login(credentials: LoginRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    now = monotonic()
    login_attempts[client] = [attempt for attempt in login_attempts[client] if now - attempt < 300]
    if len(login_attempts[client]) >= 5:
        raise HTTPException(status_code=429, detail="尝试次数过多，请五分钟后再试")
    if credentials.username != os.environ.get("AUTH_USERNAME", "admin") or not auth.verify_password(credentials.password, PASSWORD_HASH):
        login_attempts[client].append(now)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    login_attempts.pop(client, None)
    response = JSONResponse({"ok": True})
    response.set_cookie(auth.COOKIE_NAME, auth.create_session(AUTH_SECRET), max_age=auth.SESSION_SECONDS,
                        httponly=True, samesite="lax", secure=request.url.scheme == "https")
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(auth.COOKIE_NAME)
    return response


app.mount("/static_uploads", StaticFiles(directory=UPLOAD_DIR), name="static_uploads")
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")
app.include_router(router)


@app.get("/")
def read_root():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/upload")
async def upload_media(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    allowed_images = {"jpg", "jpeg", "png", "gif", "webp"}
    allowed_audio = {"mp3", "wav", "m4a", "ogg"}
    if ext not in allowed_images | allowed_audio:
        raise HTTPException(status_code=400, detail="仅支持图片或音频文件")
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOAD_DIR / unique_filename
    size = 0
    try:
        with file_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 30 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="文件不能超过 30 MB")
                target.write(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    return {
        "filename": unique_filename,
        "media_url": f"/static_uploads/{unique_filename}",
        "media_type": "image" if ext in allowed_images else "audio",
        "message": "上传成功",
    }
