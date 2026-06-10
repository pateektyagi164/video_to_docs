import asyncio
import re
import logging
from pathlib import Path

# Initialize the logger for this specific module
logger = logging.getLogger(__name__)

class MediaEngineError(Exception):
    """Custom exception for FFmpeg processing errors."""
    pass

class MediaEngine:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.frames_dir = self.workspace_dir / "frames"
        
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"MediaEngine initialized. Workspace: {self.workspace_dir} | Frames: {self.frames_dir}")

    async def extract_audio(self, video_path: str) -> str | None:
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Target video file not found at: {video_path}")
            raise FileNotFoundError(f"Target video file not found at: {video_path}")

        logger.info(f"Extracting audio from {video_path}...")
        audio_path = self.workspace_dir / "audio.wav"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path), 
            "-vn", "-acodec", "pcm_s16le", 
            "-ar", "16000", "-ac", "1", str(audio_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # --- ERROR HANDLING FOR MISSING AUDIO ---
        if process.returncode != 0:
            error_log = stderr.decode('utf-8', errors='ignore')
            # Check if the error is likely due to missing streams rather than a critical system failure
            if "does not contain any stream" in error_log or "Invalid data found" in error_log:
                logger.warning(f"No audio stream found in {video_path}. Skipping audio extraction.")
                return None
            else:
                logger.error(f"Audio extraction failed (Exit Code: {process.returncode}). Log: {error_log}")
                raise MediaEngineError(f"FFmpeg audio extraction failed. Exit code {process.returncode}.")
            
        logger.info("Audio extraction completed successfully.")
        return str(audio_path)

    async def extract_scene_frames(self, video_path: str) -> list[dict]:
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Target video file not found at: {video_path}")
            raise FileNotFoundError(f"Target video file not found at: {video_path}")

        logger.info(f"Running dynamic scene detection on {video_path}...")
        filter_str = "select='eq(n,0)+gt(scene,0.04)',showinfo"
        frame_output_pattern = self.frames_dir / "%07d.jpg"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", filter_str,
            "-fps_mode", "vfr",
            str(frame_output_pattern)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # --- ERROR HANDLING FOR MISSING VISUALS ---
        if process.returncode != 0:
            error_log = stderr.decode('utf-8', errors='ignore')
            # If it fails to find a video stream to filter, log it and return an empty timeline
            logger.warning(f"Scene extraction failed (likely no video stream). Returning empty timeline. Log snippet: {error_log[-200:]}")
            return []
        
        logs = stderr.decode('utf-8', errors='ignore')
        pattern = re.compile(r"n:\s*(\d+).*?pts_time:([0-9.]+)")
        matches = pattern.findall(logs)

        timeline = []
        for match in matches:
            frame_num = int(match[0]) + 1 
            time_sec = float(match[1])
            
            timeline.append({
                "frame": f"{frame_num:07d}.jpg",
                "start_sec": time_sec
            })

        fallback_frame = self.frames_dir / "0000001.jpg"
        if not timeline and fallback_frame.exists():
            logger.warning("No dynamic scenes detected. Falling back to default initial frame.")
            timeline.append({"frame": "0000001.jpg", "start_sec": 0.0})

        logger.info(f"Successfully detected and logged {len(timeline)} visual scenes in {self.frames_dir}.")
        return timeline