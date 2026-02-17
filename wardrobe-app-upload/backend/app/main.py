from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import auth, items, recommend

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(items.router, prefix=settings.api_prefix)
app.include_router(recommend.router, prefix=settings.api_prefix)

# Ensure tables exist for both runtime and local test clients.
Base.metadata.create_all(bind=engine)


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def root():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Wardrobe backend is running"}


@app.get(f"{settings.api_prefix}/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.get("/{file_path:path}", include_in_schema=False)
def static_files(file_path: str):
    if file_path.startswith(settings.api_prefix.strip("/") + "/") or file_path == settings.api_prefix.strip("/"):
        raise HTTPException(status_code=404, detail="API route not found")

    # SPA fallback: serve frontend files when available.
    candidate = frontend_dir / file_path
    if frontend_dir.exists() and candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(frontend_dir / "index.html")
