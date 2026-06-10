import os
import time
import logging
from pathlib import Path
from PIL import Image
from google import genai
from dotenv import load_dotenv
from app.core.config import settings

logger = logging.getLogger(__name__)
load_dotenv()

class AIDocumentGenerator:
    def __init__(self):
        api_key = settings.API_KEY
        if not api_key:
            raise ValueError("CRITICAL: GEMINI_API_KEY is missing from .env file")
        
        self.client = genai.Client(api_key=api_key)
        
        # Modernized tier pool using active production models
        self.model_pool = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
        self.active_model = self._resolve_best_model()

    def _resolve_best_model(self) -> str:
        """Queries the Google API to dynamically select the highest quality authorized model."""
        logger.info("Querying Google servers for allowed models on this API key...")
        try:
            available_models = [m.name.replace("models/", "") for m in self.client.models.list()]
            logger.info(f"Authorized models detected: {available_models}")

            # Select the highest-ranking authorized model present in our pool
            for model in self.model_pool:
                if model in available_models:
                    logger.info(f"Successfully bound AIDocumentGenerator to target model: {model}")
                    return model
            
            selected = available_models[-1]
            logger.info(f"Fallback to absolute last available model: {selected}")
            return selected

        except Exception as e:
            logger.error(f"Failed to dynamically fetch models: {e}. Defaulting to safe fallback.")
            return 'gemini-2.5-pro'
            
    def _handle_model_exhaustion(self):
        """Switches the active model to an alternative from the pool when a model fails or hits its daily cap."""
        current_index = self.model_pool.index(self.active_model) if self.active_model in self.model_pool else -1
        next_index = current_index + 1
        
        if next_index < len(self.model_pool):
            old_model = self.active_model
            self.active_model = self.model_pool[next_index]
            logger.warning(f"!!! CRITICAL HOT-SWAP !!! Diverting processing traffic from '{old_model}' to '{self.active_model}'...")
        else:
            logger.error("All models in the tier pool have exhausted their daily quotas or are unavailable.")
            raise RuntimeError("All available Gemini Tier models have completely exhausted their availability options.")

    def _format_time(self, seconds: float) -> str:
        """Helper to convert raw seconds into MM:SS or HH:MM:SS format."""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _execute_api_call_with_rate_limit_protection(self, payload: list, label: str) -> str:
        """Executes content generation while protecting against 429 minute caps, 404 retirements, and daily exhaustion."""
        max_retries = 3
        attempts = 0
        
        while attempts < max_retries:
            try:
                logger.info(f"[{label}] Sending payload to {self.active_model} (Attempt {attempts + 1}/{max_retries})...")
                response = self.client.models.generate_content(
                    model=self.active_model,
                    contents=payload
                )
                
                if not response or not response.text:
                    raise ValueError("The Gemini API returned an empty response or was blocked by safety filters.")
                
                return response.text
                
            except Exception as e:
                error_str = str(e)
                
                # Case A: 24-Hour Daily Limit Exhaustion
                if "PerDay" in error_str or "daily" in error_str.lower():
                    logger.error(f"[{label}] Model {self.active_model} hit its hard 24-hour daily limit.")
                    self._handle_model_exhaustion()
                    attempts = 0  # Reset retry counter for the fresh model swap
                    continue

                # Case B: Retired or Unsupported Legacy Model (404 Error)
                elif "404" in error_str and "not found" in error_str.lower():
                    logger.warning(f"[{label}] Model {self.active_model} returned 404 Not Found (possibly retired). Hot-swapping to alternate path...")
                    self._handle_model_exhaustion()
                    attempts = 0  # Reset retry counter for the fresh model swap
                    continue

                # Case C: Transient Per-Minute Rate Limits (429 Tokens/Requests Per Minute)
                elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    attempts += 1
                    if attempts >= max_retries:
                        logger.error(f"[{label}] Fatal: API Rate Limit hit repeatedly. Retries exhausted.")
                        raise RuntimeError(f"Gemini API Quota Exhausted permanently after {max_retries} attempts: {error_str}")
                    
                    logger.warning(f"[{label}] API Minute-Rate Limit detected (429). Freezing thread for 65 seconds to clear quota pool...")
                    time.sleep(65)
                
                # Case D: Total Systemic Breakdown (Bad API Key, invalid parameters, etc.)
                else:
                    logger.error(f"[{label}] Unrecoverable API Error encountered: {error_str}")
                    raise e

    def _build_multimodal_payload_segment(self, base_prompt: str, sub_timeline: list, frames_dir: str) -> list:
        """Converts a specific portion of the timeline cleanly into your precise payload structure."""
        payload = [base_prompt]
        frames_path = Path(frames_dir)
        
        for scene in sub_timeline:
            start_str = self._format_time(scene.get("start_time_sec", 0))
            end_str = self._format_time(scene.get("end_time_sec", 0))
            
            # Injecting the timestamp boundary
            payload.append(f"\n\n--- TIMELINE SEGMENT [{start_str} - {end_str}] ---")
            
            text = scene.get("text", "").strip()
            synced_frames = scene.get("synced_frames", [])
            
            if text:
                payload.append(f"Spoken Audio: {text}")
            
            if synced_frames:
                for frame_name in synced_frames:
                    img_path = frames_path / frame_name
                    if img_path.exists():
                        try:
                            img = Image.open(img_path)
                            payload.append(img)
                        except Exception as e:
                            logger.warning(f"Could not load image {frame_name}: {e}")
        return payload

    def generate_synthesis(self, transcription_data: dict, frames_dir: str) -> str:
        logger.info("Initializing Deep Multimodal Synthesis...")
        timeline = transcription_data.get("timeline", [])
        
        # ==========================================
        # 1. TOTAL FAILURE EDGE CASE -> DATABASE EXCEPTION
        # ==========================================
        if not timeline:
            logger.error("Timeline is completely empty. Bypassing AI generation and triggering failure.")
            raise ValueError("Media extraction yielded absolutely zero audio and zero visual frames. The file may be completely corrupted or empty.")

        # ==========================================
        # 2. DISCOVER PRESENT MODALITIES
        # ==========================================
        has_audio = any(scene.get("text", "").strip() for scene in timeline)
        has_visuals = any(scene.get("synced_frames", []) for scene in timeline)

        # ==========================================
        # 3. THE DYNAMIC EDUCATIONAL SYSTEM PROMPT
        # ==========================================
        prompt = (
            "You are a Master Technical Analyst, Professor, and Documentation Engineer. "
            "I am providing you with a chronological timeline of an educational presentation. "
            "This content could be from ANY field (Computer Science, Medicine, Mathematics, History, Physics, etc.).\n\n"
            
            "YOUR MISSION:\n"
            "Synthesize this raw data into a highly structured, exhaustive, and standalone technical textbook-style article in Markdown format. "
            "The final document must completely replace the need for a student to consume the original media.\n\n"
            
            "STRICT RULES:\n"
            "1. CHRONOLOGICAL BOUNDARIES: I have separated the data into explicit timestamped segments. You must synthesize the information STRICTLY within their associated time blocks. Do not hallucinate data across segments.\n"
            "2. ZERO META-REFERENCES: You are writing a native article. NEVER mention the existence of the video, timestamps, slides, audio, or images. "
            "DO NOT write phrases like 'At 01:30', 'In the provided image', or 'The speaker says'.\n"
            "3. PROFESSIONAL STRUCTURE: \n"
            "   - Begin with a descriptive `# Title` and an `Executive Summary`.\n"
            "   - Break the content into logical, flowing sections using `##` and `###` headers based on topic shifts, not just time shifts.\n"
            "   - Heavily utilize markdown: use bullet points, tables, **bold text** for emphasis, and ``` code blocks ``` for any programming or syntax detected.\n"
        )

        # Inject modality-specific rules
        if has_audio and has_visuals:
            prompt += (
                "4. MULTIMODAL EXTRACTION: You will receive both spoken audio text and physical visual frames. "
                "If a frame contains mathematical formulas, code snippets, architectural diagrams, medical charts, bullet points, or UI elements, "
                "you MUST extract that exact information and explicitly write it into the document. leave no educational value behind.\n"
                "5. CONTEXTUAL FUSION: If the spoken audio uses pointer words ('As you can see here', 'Notice this equation'), "
                "you must use the visual frame provided in that exact time segment to deduce what they are referring to. Fuse the visual context with the spoken context seamlessly.\n"
                "6. NO IMAGE LINKS: Do not attempt to embed Markdown image links. Translate all visual diagrams and flowcharts completely into descriptive text, tables, or ASCII/Markdown formatting.\n"
            )
        elif has_visuals and not has_audio:
            prompt += (
                "4. VISUAL-ONLY EXTRACTION: The provided media is SILENT. You will receive ONLY visual frames. "
                "You must rely entirely on on-screen text, mathematical formulas, code snippets, diagrams, charts, and visual transitions to generate the document. "
                "You MUST extract all visible information and explicitly write it into the document. Do not invent spoken context.\n"
                "5. NO IMAGE LINKS: Do not attempt to embed Markdown image links. Translate all visual diagrams and flowcharts completely into descriptive text, tables, or ASCII/Markdown formatting.\n"
            )
        elif has_audio and not has_visuals:
            prompt += (
                "4. AUDIO-ONLY EXTRACTION: The provided media has NO VISUALS. You will receive ONLY spoken audio transcripts. "
                "You must rely entirely on the spoken context to structure the document. "
                "Do NOT invent or assume visual elements, diagrams, or on-screen text that is not explicitly described in the audio.\n"
            )

        prompt += "\nAnalyze the timeline step-by-step and generate the ultimate comprehensive educational document."

        # ==========================================
        # 4. ARCHITECTURAL BRANCHING (SURVIVAL MODES)
        # ==========================================
        CHUNK_SIZE = 60 # Coarser granular chunk size prevents burning requests per day limits

        if len(timeline) <= CHUNK_SIZE:
            # SHORT VIDEO: Run original pipeline monolithic pass
            logger.info(f"Short timeline detected ({len(timeline)} scenes). Executing Single-Pass Multimodal Generation.")
            payload = self._build_multimodal_payload_segment(prompt, timeline, frames_dir)
            
            final_text = self._execute_api_call_with_rate_limit_protection(payload, "Monolithic Generation")
            logger.info("Document successfully synthesized via Single-Pass.")
            return final_text

        else:
            # LONG VIDEO: Map-Reduce Chunking Route
            logger.info(f"Long timeline detected ({len(timeline)} scenes). Slicing into Map-Reduce intervals.")
            
            timeline_chunks = [timeline[i:i + CHUNK_SIZE] for i in range(0, len(timeline), CHUNK_SIZE)]
            total_chunks = len(timeline_chunks)
            chapter_notes = []

            chunk_specific_prompt = prompt + "\n\nCRITICAL CONTEXT: You are processing a subset/chapter of a larger presentation. Focus entirely on extracting and writing comprehensive data for this timeline slice without wrapping it in an introduction or concluding remarks."

            # Step A: MAP Phase
            for index, current_chunk in enumerate(timeline_chunks):
                logger.info(f"Slicing timeline: Processing block {index + 1} of {total_chunks}...")
                chunk_payload = self._build_multimodal_payload_segment(chunk_specific_prompt, current_chunk, frames_dir)
                
                chunk_response_text = self._execute_api_call_with_rate_limit_protection(
                    chunk_payload, 
                    f"Chunk {index + 1}/{total_chunks}"
                )
                
                chapter_notes.append(f"\n\n## PRESENTATION SEGMENT SECTION {index + 1}\n{chunk_response_text}")

            # Step B: REDUCE Phase
            logger.info("All timeline sub-blocks successfully mapped. Commencing final consolidation phase...")
            
            reduce_prompt = (
                "You are a Master Editorial Team and Lead Technical Documentation Engineer. "
                "I am providing you with highly descriptive text chapters extracted from an educational media presentation.\n\n"
                
                "YOUR MISSION:\n"
                "Unify and merge these raw chapter blocks into a single, perfectly flowing, high-quality textbook-style article in Markdown format.\n\n"
                
                "STRICT STRUCTURAL EDITING RULES:\n"
                "1. Begin with a descriptive, professional top-level `# Title` and a thorough `Executive Summary` mapping the entire scope of the content.\n"
                "2. Transform the temporary section headers seamlessly into clean thematic `##` and `###` structural headers based entirely on logical topic flow.\n"
                "3. Remove all redundant text transitions between chapters. The final document must read smoothly as though it was originally written as a single unified piece from start to finish.\n"
                "4. Maintain every detail, code block, formula, bullet point, and data metric present within the source materials. Do not compress or drop technical depth.\n"
                "5. ZERO META-REFERENCES: Do not reference internal segment labels, chapter numbers, videos, or raw input artifacts. It must be a native article.\n\n"
                "Here is the chronological presentation data:\n"
            )

            reduce_payload = [reduce_prompt] + chapter_notes
            
            final_document = self._execute_api_call_with_rate_limit_protection(reduce_payload, "Master Consolidation")
            logger.info("Document successfully synthesized via Map-Reduce Consolidation.")
            return final_document