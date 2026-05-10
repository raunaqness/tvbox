from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app.models.db import Base, engine
from app.routers import api

# Initialize database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auto-Stream")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(api.router)

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
