# 🧠 Distributed Multimodal Synthesis Engine
> **An asynchronous, fault-tolerant AI pipeline that autonomously synthesizes raw educational videos into structured Markdown textbooks by aligning pixel-delta visual frames with audio transcripts.**

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Celery](https://img.shields.io/badge/celery-%2337814A.svg?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![OpenAI Whisper](https://img.shields.io/badge/OpenAI%20Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)

---

## 📖 Overview
The Multimodal Synthesis Engine solves the computational bottlenecks of large-scale video processing by decoupling HTTP ingestion from heavy Machine Learning inference. 

Instead of relying on basic LLM transcription wrappers, this architecture utilizes custom algorithmic synchronization to map visual changes (extracted via FFmpeg) to specific audio timestamps (transcribed via Whisper). By offloading this compute to a Redis/Celery background queue, it safely processes massive files, evades LLM context exhaustion via Map-Reduce chunking, and streams real-time state machine progress back to the React client.

---

## ⚙️ The Data Pipeline & Workflow

How does a 1GB `.mp4` file become a clean PDF textbook? The system processes data in 5 distinct phases:

### Phase 1: Ingestion & Job Delegation (FastAPI & Redis)
1. The user drops a video file into the React interface.
2. The **FastAPI** web server receives the multi-part form data and writes the raw binary to ephemeral storage.
3. FastAPI creates a new Job Record in the **PostgreSQL** database (via SQLModel).
4. FastAPI dispatches an asynchronous task to the **Redis** message broker and immediately responds to the client with a `job_id`.
5. The React client opens a Server-Sent Events (SSE) connection to listen for live status updates.

### Phase 2: Dual-Modal Extraction (FFmpeg & Whisper)
1. The **Celery Worker** picks up the task from Redis.
2. **Visual Extraction:** The worker spawns an **FFmpeg** subprocess using custom pixel-delta scene detection filters (`select='gt(scene,0.03)'`). Instead of pulling every frame, it only saves frames where the visual content significantly changes (e.g., a slide transition or new code block).
3. **Audio Extraction:** Simultaneously, the audio track is stripped and fed into **OpenAI Whisper**. Whisper returns a highly accurate, timestamped JSON array of spoken segments.

### Phase 3: Algorithmic Temporal Synchronization
*This is the core algorithmic engine of the project.*
1. The system holds an array of visual frames (with creation timestamps) and an array of spoken sentences (with start/end timestamps).
2. The worker executes an **O(log M) Binary Search Algorithm** to perfectly map each visual frame to the exact sentence that was spoken while that frame was on screen.
3. This creates a deeply contextual "Fused Block" of data where visuals and audio are bound together mathematically.

### Phase 4: Map-Reduce LLM Synthesis (Gemini 1.5 Pro)
1. Sending a massive array of images and text to an LLM at once causes token exhaustion and rate-limit crashes.
2. The worker implements a **Map-Reduce Chunking Strategy**, slicing the fused data into chronological blocks of 60 scenes.
3. Each block is sent to the **Google Gemini Large Multimodal Model (LMM)** with strict prompt grounding to extract academic concepts, formulas, and summaries.
4. If Google's API returns a `429 Too Many Requests` error, the Celery worker triggers a 65-second watchdog sleep thread and automatically retries.

### Phase 5: Assembly & Delivery
1. The individual summaries are dynamically merged (Reduced) into a single, cohesive Markdown document.
2. The document string is saved to the PostgreSQL database.
3. The SSE stream notifies the React client that the job is complete.
4. The client retrieves the Markdown, renders it via `react-markdown`, and utilizes native browser APIs (`react-to-print`) to export a highly styled PDF.

---

## 📂 System Architecture

```text
VIDEO_TO_DOCS/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI Routes & SSE Event Streams
│   │   ├── core/          # PostgreSQL & Celery configurations
│   │   ├── models/        # SQLModel ORM Schemas for Job State
│   │   ├── services/      # FFmpeg Engine, Binary Search Sync, Gemini Inference
│   │   └── worker/        # Celery Task Definitions
│   ├── Dockerfile         # Production container spec for Web & Worker
│   └── main.py            # Uvicorn Application Entrypoint
└── frontend/
    ├── src/
    │   ├── api/           # Axios Interceptors & dynamic environment routing
    │   ├── components/    # UploadZone, ProgressBar, DocumentViewer
    │   └── App.jsx        # React 18 State Machine Orchestrator
    └── tailwind.config.js # Tailwind CSS v4 OKLCH configuration
