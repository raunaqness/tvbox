from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app.models.db import Base, engine, ensure_job_schema
from app.routers import api

# Initialize database
Base.metadata.create_all(bind=engine)
ensure_job_schema()

app = FastAPI(title="tvbox")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Public paths
        if request.url.path in ["/login", "/api/health"] or request.url.path.startswith("/static"):
            return await call_next(request)
        
        if not request.session.get("authenticated"):
            if request.url.path.startswith("/api"):
                from fastapi import Response
                return Response("Unauthorized", status_code=401)
            return RedirectResponse(url="/login")
        
        return await call_next(request)

# Order matters: SessionMiddleware must be OUTSIDE AuthMiddleware
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "fallback_secret"))

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

from app.routers import auth
app.include_router(api.router)
app.include_router(auth.router)

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
