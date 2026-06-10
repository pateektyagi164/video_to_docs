import whisper
import os
import bisect
import logging

logger = logging.getLogger(__name__)

class AITranscriber:
    def __init__(self):
        logger.info("Loading Whisper AI Model into memory...")
        # Note: Depending on your system, you might want to load this lazily 
        # or handle device placement (CPU/GPU)
        self.model = whisper.load_model("base")
        
    def transcribe_and_sync(self, audio_path: str | None, visual_timeline: list[dict]) -> dict:
        logger.info("Running AI Multi-Frame Intersection Alignment...")

        if not (audio_path or not os.path.exists(audio_path)) and not visual_timeline:
            logger.error("CRITICAL: Both audio and visual data are missing. Aborting sync.")
            # Returning an empty standard structure perfectly triggers 
            # the "TOTAL FAILURE EDGE CASE" in your AIDocumentGenerator!
            return {
                "full_text": "",
                "timeline": [] 
            }
        
        # ==========================================
        # EDGE CASE 1: NO AUDIO (SILENT VIDEO)
        # ==========================================
        if not audio_path or not os.path.exists(audio_path):
            logger.warning("Audio track missing or not provided. Processing as Visual-Only timeline.")
            synced_data = []
            
            for i in range(len(visual_timeline)):
                start_time = visual_timeline[i]["start_sec"]
                # Calculate end time based on the next frame, or infinity for the last frame
                end_time = visual_timeline[i + 1]["start_sec"] if i + 1 < len(visual_timeline) else 999999.0
                
                synced_data.append({
                    "start_time_sec": round(start_time, 2),
                    "end_time_sec": round(end_time, 2),
                    "text": "",  # Empty transcript
                    "synced_frames": [visual_timeline[i]["frame"]]
                })
                
            return {
                "full_text": "",
                "timeline": synced_data
            }

        # ==========================================
        # NORMAL TRANSCRIPTION PROCEEDS HERE
        # ==========================================
        logger.info(f"Transcribing audio from: {audio_path}")
        result = self.model.transcribe(audio_path)
        segments = result["segments"]
        
        # ==========================================
        # EDGE CASE 2: NO VISUALS (AUDIO ONLY)
        # ==========================================
        if not visual_timeline:
            logger.warning("Visual timeline is empty. Processing as Audio-Only timeline.")
            synced_data = []
            
            for seg in segments:
                synced_data.append({
                    "start_time_sec": round(seg["start"], 2),
                    "end_time_sec": round(seg["end"], 2),
                    "text": seg["text"].strip(),
                    "synced_frames": []  # Empty frames list
                })
                
            return {
                "full_text": result["text"].strip(),
                "timeline": synced_data
            }

        # ==========================================
        # THE "HAPPY PATH": AUDIO + VISUALS
        # ==========================================
        synced_data = []
        end_times = []
        
        # Step 1: Compute operational windows
        for i in range(len(visual_timeline)):
            start_time = visual_timeline[i]["start_sec"]
            end_time = visual_timeline[i + 1]["start_sec"] if i + 1 < len(visual_timeline) else 999999.0
            
            visual_timeline[i]["end_sec"] = end_time
            end_times.append(end_time)

        # Step 2: O(log M) Binary Search Intersection
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            
            overlapping_frames = []
            start_index = bisect.bisect_right(end_times, seg_start)

            for i in range(start_index, len(visual_timeline)):
                scene = visual_timeline[i]
                
                if scene["start_sec"] >= seg_end:
                    break
                    
                overlap_start = max(seg_start, scene["start_sec"])
                overlap_end = min(seg_end, scene["end_sec"])
                
                if overlap_start < overlap_end:
                    overlapping_frames.append(scene["frame"])

            if not overlapping_frames and len(visual_timeline) > 0:
                overlapping_frames.append(visual_timeline[-1]["frame"])

            synced_data.append({
                "start_time_sec": round(seg_start, 2),
                "end_time_sec": round(seg_end, 2),
                "text": seg["text"].strip(),
                "synced_frames": overlapping_frames
            })

        return {
            "full_text": result["text"].strip(),
            "timeline": synced_data
        }