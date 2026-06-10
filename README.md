# 🧠 Distributed Multimodal Synthesis Engine
> **An enterprise-grade, asynchronous AI pipeline that autonomously transforms raw educational videos into structured, textbook-style Markdown documents by perfectly synchronizing visual and acoustic data.**

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Celery](https://img.shields.io/badge/celery-%2337814A.svg?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)

## 📖 Overview
The Multimodal Synthesis Engine is built to eliminate the need for manual video review. It operates as a full-scale distributed system that extracts, aligns, and synthesizes complex multimodal data. 

Instead of relying on simple transcription wrappers, this architecture utilizes custom algorithmic synchronization to map pixel-delta visual changes to specific audio timestamps. By offloading this heavy compute to a background task queue, it processes massive files safely, evades LLM context exhaustion via Map-Reduce chunking, and streams real-time progress back to the client.

## ✨ Core Architecture & Features
* **End-to-End AI Synthesis:** Autonomously extracts both audio and visual data from raw video files to generate comprehensive, standalone educational materials and textbooks.
* **Algorithmic Temporal Synchronization:** Utilizes an **O(log M) binary search** algorithm to precisely map dynamic visual frames—extracted via customized FFmpeg pixel-delta scene detection—to exact OpenAI Whisper audio transcript time windows.
* **Asynchronous Task Queue:** Architected a highly resilient distributed processing engine using **FastAPI**, **Celery**, and **Redis** to offload heavy media extraction and LLM inference, preventing API timeouts and ensuring backend fault tolerance.
* **Map-Reduce LLM Orchestration:** Implements a chronological chunking strategy for **Gemini 1.5 Pro/Flash** Large Multimodal Models (LMMs) to bypass token limits, equipped with state machine watchdog timers and 429-rate-limit handling.
* **Real-Time Client Architecture:** A **React 18** frontend utilizes Server-Sent Events (SSE) for live asynchronous worker tracking, paired with native DOM-to-PDF rendering for pristine document export.

## 🛠️ Tech Stack
* **Backend Pipeline:** Python, FastAPI, Celery, Redis, SQLModel, PostgreSQL
* **Generative AI & Media:** Google GenAI (Gemini 1.5), OpenAI Whisper, FFmpeg, Pillow
* **Frontend Interface:** React 18, Vite, Tailwind CSS v4, `react-markdown`, `react-to-print`

## 📂 System Flow & Structure
```text
VIDEO_TO_DOCS/
├── backend/
│   ├── app/
│   │   ├── api/           # HTTP Routes & SSE Event Streams
│   │   ├── core/          # PostgreSQL & Celery configurations
│   │   ├── models/        # SQLModel ORM Schemas for Job State
│   │   ├── services/      # FFmpeg Subprocesses, Temporal Sync, LLM Inference
│   │   └── worker/        # Celery Task Definitions
│   ├── local_workspace/   # Ephemeral storage for frame/audio extraction
│   └── main.py            # Uvicorn Application Entrypoint
└── frontend/
    ├── src/
    │   ├── api/           # Axios Interceptors & Client
    │   ├── components/    # UploadZone, ProgressBar, DocumentViewer
    │   ├── index.css      # Tailwind v4 Directives & OKLCH support
    │   └── App.jsx        # Component State Orchestrator
    └── tailwind.config.js
