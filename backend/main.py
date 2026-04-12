# backend/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.auth_routes import router as auth_router
from backend.api.cases_routes import router as cases_router
from backend.api.drafts_routes import router as drafts_router
from backend.api.pipeline_routes import router as pipeline_router
from backend.api.lawyer_routes import router as lawyer_router
from backend.api.notify_routes import router as notify_router
from backend.db.firestore_client import seed_demo_case

app = FastAPI(title="JusticIA API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api", tags=["cases"])
app.include_router(drafts_router, prefix="/api", tags=["drafts"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(lawyer_router, prefix="/api/lawyer", tags=["lawyer"])
app.include_router(notify_router, prefix="/api/notify", tags=["notify"])


@app.on_event("startup")
async def startup():
    seed_demo_case()


@app.get("/health")
async def health():
    return {"status": "ok"}


_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_frontend_index = _frontend_dist / "index.html"

if _frontend_dist.is_dir() and _frontend_index.is_file():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_index)
