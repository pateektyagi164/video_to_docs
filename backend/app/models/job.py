from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Enum, JSON,Text # <-- CRITICAL: Import JSON from sqlalchemy
import uuid
from datetime import datetime
import enum

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingJob(SQLModel, table=True):
    __tablename__ = "processing_jobs"

    # UUID prevents ID-guessing attacks
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Store the original video name or path
    video_path: str 
    
    # Track the state of the background worker
    status: JobStatus = Field(sa_column=Column(Enum(JobStatus), default=JobStatus.PENDING))
    
    # If the job fails, we store the error here so the user knows why
    error_message: str | None = None
    
    # Audit timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # --- THE ARCHITECTURE UPGRADE ---
    # Replaced 'transcription: str' with a structured JSON column to hold 
    # the dictionary containing 'full_text' and the 'timeline' array.
    transcription_data: str = Field(default="",sa_column=Column(Text))