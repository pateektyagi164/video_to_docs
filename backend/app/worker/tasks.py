import asyncio
import logging
from sqlmodel import Session
import json 
import redis
import time
from app.core.celery_app import celery_app
from app.core.db import engine
from app.models.job import ProcessingJob, JobStatus
from app.services.media_engine import MediaEngine
from app.services.transcriber import AITranscriber
from app.services.document_generator import AIDocumentGenerator

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=1)

# Initialize singletons outside the task to optimize memory reuse
doc_generator = AIDocumentGenerator()
ai_engine = AITranscriber()

import json

def update_progress(job_id: str, step: str, percent: int, final_data: str = None):
    """Helper to push progress payload to Redis. Attaches document or error on finish."""
    payload = {
        "step": step, 
        "percent": percent
    }
    
    # If it's 100%, attach the generated Markdown document
    if percent == 100 and final_data:
        payload["document"] = final_data
        
    # If it failed (-1%), attach the exact error message
    elif percent == -1 and final_data:
        payload["error"] = final_data

    # json.dumps safely escapes all markdown formatting and newlines!
    redis_client.setex(f"job_progress:{job_id}", 3600, json.dumps(payload))

@celery_app.task(bind=True, name="process_video_task")
def process_video_task(self, job_id: str):
    """
    Background worker that extracts audio/video features, runs Whisper alignment,
    and calls the Gemini Multimodal synthesis model to generate technical docs.
    """
    # 1. Fetch job metadata and free the DB connection pool immediately
    with Session(engine) as session:
        job = session.get(ProcessingJob, job_id)
        if not job:
            logger.error(f"Error: Job {job_id} not found in database.")
            return f"Error: Job {job_id} not found in database."

        # Mark the job as PROCESSING
        job.status = JobStatus.PROCESSING
        session.add(job)
        session.commit()
        
        # Cache properties locally so we can use them while disconnected
        video_path = job.video_path

    # 2. Execute heavy computing and API calls safely outside the active DB session
    try:
        workspace = f"local_workspace/job_{job_id}"
        engine_instance = MediaEngine(workspace_dir=workspace)
        update_progress(job_id, "Extracting Audio and Visual Frames", 10)
        
        # Asynchronous Parallel Extraction
        async def run_extraction_pipeline():
            audio_task = engine_instance.extract_audio(video_path)
            visual_task = engine_instance.extract_scene_frames(video_path)
            
            # Fire both FFmpeg sub-processes concurrently (O(1) parallel wait time)
            audio_path, visual_timeline = await asyncio.gather(audio_task, visual_task)
            return audio_path, visual_timeline
        
        logger.info(f"Starting parallel extraction pipeline for job {job_id}")
        extracted_audio_path, visual_timeline = asyncio.run(run_extraction_pipeline())

        # Run AI Whisper Alignment (O(N log M) Binary Search Optimized)
        logger.info(f"Handing data to AI Transcriber for job {job_id}")

        update_progress(job_id, "Transcribing and Aligning Audio", 40)
        ai_data = ai_engine.transcribe_and_sync(extracted_audio_path, visual_timeline)


        # Generate Deep Multimodal Synthesis Document via Gemini
        logger.info(f"Generating final document via Gemini for job {job_id}")
        frames_directory = str(engine_instance.frames_dir)

        update_progress(job_id, "Generating Deep Multimodal Synthesis", 70)

        final_markdown_doc = doc_generator.generate_synthesis(
            transcription_data=ai_data, 
            frames_dir=frames_directory
        )

        # Inject the synthesized article directly into our timeline mapping dictionary
        
        # 3. Open a fresh transaction block to persist the completed results
        with Session(engine) as session:
            live_job = session.get(ProcessingJob, job_id)
            if live_job:
                live_job.transcription_data = final_markdown_doc
                live_job.status = JobStatus.COMPLETED
                session.add(live_job)
                session.commit()
        
        logger.info(f"Job {job_id} completely finished.")
        update_progress(job_id, "Completed", 100, final_data=final_markdown_doc)
        return f"Job {job_id} completed."

    except Exception as e:
        logger.error(f"CRASH DETECTED in worker for job {job_id}: {str(e)}") 
        # Crash Recovery Block: Open a fresh session to record the exact error trail
        with Session(engine) as session:
            live_job = session.get(ProcessingJob, job_id)
            if live_job:
                live_job.status = JobStatus.FAILED
                live_job.error_message = str(e)
                session.add(live_job)
                session.commit()
        update_progress(job_id, f"Failed: {str(e)}", -1, final_data=str(e))       
        return f"Job {job_id} FAILED: {str(e)}"