from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Dict, Any
from app.services.tmdb import TMDBClient
from app.services.search import SearchAggregator, YTSStrategy, ProwlarrStrategy, PirateBayStrategy
from app.services.download import DownloadManager
from app.services.upload import UploadManager
from app.models.db import SessionLocal, Job
from pydantic import BaseModel
import asyncio
import uuid

router = APIRouter()
tmdb_client = TMDBClient()
search_aggregator = SearchAggregator([YTSStrategy(), ProwlarrStrategy(), PirateBayStrategy()])
download_manager = DownloadManager()
upload_manager = UploadManager()

class FetchRequest(BaseModel):
    query: str
    year: str = ""

@router.get("/api/search")
async def search_tmdb(q: str):
    if not q:
        return []
    return await tmdb_client.search(q)

@router.post("/api/fetch")
async def fetch_torrent(request: FetchRequest, background_tasks: BackgroundTasks):
    query = request.query
    if request.year:
        query = f"{query} {request.year}"
        
    results = await search_aggregator.aggregate_search(query)
    if not results:
        raise HTTPException(status_code=404, detail="No torrents found.")
        
    best_torrent = results[0]
    
    gid = download_manager.add_magnet(best_torrent.magnet)
    if not gid:
        raise HTTPException(status_code=500, detail="Failed to add to download manager.")
        
    task_id = str(uuid.uuid4())
    
    db = SessionLocal()
    new_job = Job(
        id=task_id,
        gid=gid,
        title=best_torrent.title,
        status="downloading",
        progress_string="0%",
        download_speed="0 B/s"
    )
    db.add(new_job)
    db.commit()
    db.close()
    
    background_tasks.add_task(orchestrate_download_and_upload, task_id)
    return {"message": "Started", "task_id": task_id, "torrent": best_torrent.model_dump()}

@router.get("/api/status")
async def get_status():
    db = SessionLocal()
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    tasks = [
        {
            "id": j.id,
            "title": j.title,
            "status": j.status,
            "progress_string": j.progress_string,
            "download_speed": j.download_speed
        } for j in jobs
    ]
    db.close()
    return {"tasks": tasks}

async def orchestrate_download_and_upload(task_id: str):
    is_complete = False
    download_name = None
    
    while not is_complete:
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == task_id).first()
        if not job:
            db.close()
            return
            
        gid = job.gid
        progress = download_manager.get_progress(gid)
        
        if not progress:
            job.status = "failed"
            db.commit()
            db.close()
            return
            
        gid = progress["gid"]
        job.gid = gid
        download_name = progress.get("name")
            
        if progress.get("is_complete"):
            is_complete = True
            job.status = "uploading"
            job.progress_string = "100%"
            db.commit()
        else:
            job.progress_string = progress.get("progress_string", "0%")
            job.download_speed = progress.get("download_speed", "0 B/s")
            db.commit()
            
        db.close()
        
        if not is_complete:
            await asyncio.sleep(2)
            
    # Trigger Upload Phase
    if download_name:
        download_path = f"{upload_manager.downloads_dir}/{download_name}"
        success = upload_manager.upload_file(download_path)
        db = SessionLocal()
        job = db.query(Job).filter(Job.id == task_id).first()
        if job:
            if success:
                job.status = "completed"
                download_manager.remove_download(job.gid)
            else:
                job.status = "upload_failed"
            db.commit()
        db.close()
        
    upload_manager.cleanup_empty_dirs()
