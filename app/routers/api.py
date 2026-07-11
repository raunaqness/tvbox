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
    season: int = None
    episode: int = None

class DownloadRequest(BaseModel):
    magnet: str
    title: str
    fallback_magnets: List[str] = []
    media_type: str = "movie"

@router.get("/api/search")
async def search_tmdb(q: str):
    if not q:
        return []
    return await tmdb_client.search(q)

@router.get("/api/tv/{tv_id}")
async def get_tv_details(tv_id: int):
    return await tmdb_client.get_tv_details(tv_id)

@router.get("/api/tv/{tv_id}/season/{season_number}")
async def get_season_details(tv_id: int, season_number: int):
    return await tmdb_client.get_season_details(tv_id, season_number)

@router.post("/api/search_torrents")
async def search_torrents(request: FetchRequest):
    base_query = request.query
    if request.year and not request.season:
        base_query = f"{base_query} {request.year}"
        
    results = []
    if request.season is not None:
        if request.episode is not None:
            query = f"{base_query} S{request.season:02d}E{request.episode:02d}"
            results = await search_aggregator.aggregate_search(query)
        else:
            query1 = f"{base_query} S{request.season:02d}"
            query2 = f"{base_query} Season {request.season}"
            query3 = f"{base_query} Season {request.season:02d}"
            
            res_list = await asyncio.gather(
                search_aggregator.aggregate_search(query1),
                search_aggregator.aggregate_search(query2),
                search_aggregator.aggregate_search(query3),
                return_exceptions=True
            )
            
            seen = set()
            for r in res_list:
                if not isinstance(r, Exception):
                    for torrent in r:
                        if torrent.magnet not in seen:
                            seen.add(torrent.magnet)
                            results.append(torrent)
                            
            # Sort the aggregated results
            def get_sort_key(res) -> tuple:
                title_lower = res.title.lower()
                res_str = res.resolution.lower()
                score = 1
                if "2160p" in title_lower or "4k" in title_lower or "2160p" in res_str or "4k" in res_str:
                    score = 4
                elif "1080p" in title_lower or "1080p" in res_str:
                    score = 3
                elif "720p" in title_lower or "720p" in res_str:
                    score = 2
                if res.seeders < 5:
                    score -= 1.5
                return (score, res.seeders)
                
            results.sort(key=get_sort_key, reverse=True)
            
        results = [r for r in results if r.source != "YTS"]
    else:
        results = await search_aggregator.aggregate_search(base_query)
        
    if not results:
        raise HTTPException(status_code=404, detail="No torrents found.")
        
    # Return top 10 results
    return results[:10]

@router.post("/api/fetch")
async def fetch_torrent(request: DownloadRequest, background_tasks: BackgroundTasks):
    import json
    
    gid = download_manager.add_magnet(request.magnet)
    if not gid:
        raise HTTPException(status_code=500, detail="Failed to add to download manager.")
        
    task_id = str(uuid.uuid4())
    
    db = SessionLocal()
    new_job = Job(
        id=task_id,
        gid=gid,
        title=request.title,
        status="downloading",
        progress_string="0%",
        download_speed="0 B/s",
        fallback_magnets=json.dumps(request.fallback_magnets),
        media_type=request.media_type
    )
    db.add(new_job)
    db.commit()
    db.close()
    
    background_tasks.add_task(orchestrate_download_and_upload, task_id)
    return {"message": "Started", "task_id": task_id, "torrent": {"title": request.title, "magnet": request.magnet}}

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
            "download_speed": j.download_speed,
            "media_type": getattr(j, "media_type", "movie")
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
        
        # Auto-Fallback System Check
        import json
        from datetime import datetime
        if progress.get("progress_string") == "0.00%":
            # If stuck at 0.00% for > 30 minutes (1800 seconds)
            if (datetime.utcnow() - job.created_at).total_seconds() > 1800:
                fallback_list = json.loads(job.fallback_magnets) if job.fallback_magnets else []
                if fallback_list:
                    download_manager.remove_download(gid)
                    next_magnet = fallback_list.pop(0)
                    new_gid = download_manager.add_magnet(next_magnet)
                    if new_gid:
                        job.gid = new_gid
                        job.fallback_magnets = json.dumps(fallback_list)
                        job.created_at = datetime.utcnow()
                        db.commit()
                        db.close()
                        await asyncio.sleep(5)
                        continue
                else:
                    # No more fallbacks available, fail the job
                    download_manager.remove_download(gid)
                    job.status = "failed"
                    db.commit()
                    db.close()
                    return
            
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
        success = await upload_manager.upload_file(download_path)
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

async def retry_upload_only(task_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == task_id).first()
    if not job:
        db.close()
        return

    import os
    download_name = None
    if os.path.exists(upload_manager.downloads_dir):
        for name in os.listdir(upload_manager.downloads_dir):
            if job.title in name or name in job.title:
                download_name = name
                break
                
    if not download_name:
        progress = download_manager.get_progress(job.gid)
        if progress and progress.get("name"):
            download_name = progress.get("name")
            
    if not download_name:
        job.status = "failed"
        db.commit()
        db.close()
        return
        
    download_path = f"{upload_manager.downloads_dir}/{download_name}"
    success = await upload_manager.upload_file(download_path)
    
    if success:
        job.status = "completed"
        download_manager.remove_download(job.gid)
    else:
        job.status = "upload_failed"
        
    db.commit()
    db.close()
    upload_manager.cleanup_empty_dirs()

@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == task_id).first()
    if not job:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")
        
    if job.gid:
        download_manager.remove_download(job.gid)
        
    db.delete(job)
    db.commit()
    db.close()
    return {"message": "Task deleted"}

@router.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == task_id).first()
    if not job:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")
        
    if job.status not in ["upload_failed", "failed"]:
        db.close()
        raise HTTPException(status_code=400, detail="Only failed uploads can be retried")
        
    job.status = "uploading"
    db.commit()
    db.close()
    
    background_tasks.add_task(retry_upload_only, task_id)
    return {"message": "Retry started"}
