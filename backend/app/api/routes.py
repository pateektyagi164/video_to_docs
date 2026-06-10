import mimetypes
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Path as FastApiPath, File, UploadFile
from sqlmodel import Session
from pydantic import BaseModel
from app.core.db import get_session
from app.models.job import ProcessingJob, JobStatus
from app.worker.tasks import process_video_task
import json
import redis.asyncio as aioredis # Use async redis for FastAPI
from fastapi.responses import StreamingResponse
async_redis = aioredis.Redis(host='localhost', port=6379, db=1)

router = APIRouter(prefix="/api/v1")

class ExtractionRequest(BaseModel):
    video_path: str

@router.get("/progress/{job_id}")
async def stream_job_progress(job_id: Annotated[str, FastApiPath(..., description="The UUID of the job")]):
    """
    Server-Sent Events endpoint to stream processing progress.
    """
    async def event_generator():
        while True:
            # 1. Read the current progress from Redis
            data = await async_redis.get(f"job_progress:{job_id}")
            
            if data:
                # 2. Decode the JSON payload
                decoded_data = data.decode('utf-8')
                parsed_data = json.loads(decoded_data)
                
                # 3. Yield in standard SSE format
                yield f"data: {decoded_data}\n\n"
                
                # 4. Terminate the connection safely if finished or failed
                if parsed_data.get("percent") == 100 or parsed_data.get("percent") == -1:
                    break
            else:
                # If Redis key doesn't exist yet, emit a pending state
                yield f"data: {json.dumps({'step': 'Initializing pipeline...', 'percent': 0})}\n\n"

            # 5. Prevent CPU blocking, stream updates every 1 second
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/extract")
async def extract_video_endpoint(
    video_file: UploadFile = File(...), # UPGRADED: Accept actual file data
    session: Session = Depends(get_session)
):
    # 1. Validate file type
    if not video_file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=415,
            detail=f"Invalid file type. Expected a video, got: {video_file.content_type}"
        )

    # 2. Universal Path Generation: Save the file safely to the backend server
    workspace_dir = Path("local_workspace")
    workspace_dir.mkdir(exist_ok=True) # Ensure the folder exists
    
    # Create a unique filename so multiple users don't overwrite each other
    safe_filename = f"{uuid.uuid4()}_{video_file.filename}"
    saved_file_path = workspace_dir / safe_filename
    
    try:
        # Stream the uploaded bytes directly to the local disk
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 3. Save the dynamically generated absolute/relative path to PostgreSQL
    # Now Celery will know EXACTLY where the file is, no matter where it came from!
    new_job = ProcessingJob(video_path=str(saved_file_path))
    session.add(new_job)
    session.commit()
    session.refresh(new_job) 

    # 4. Throw the sticky note to Redis (Celery)
    process_video_task.delay(str(new_job.id))

    return {
        "status": new_job.status,
        "message": "Video successfully uploaded and queued for processing.",
        "job_id": new_job.id
    }