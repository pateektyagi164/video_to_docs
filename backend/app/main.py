from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router as extraction_router
from app.core.db import create_db_and_tables
from fastapi.middleware.cors import CORSMiddleware

# This function runs exactly ONCE when the server boots up

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP PHASE ---
    print("Server starting up... connecting to database...")
    create_db_and_tables() # <--- HERE IS WHERE IT GETS CALLED!
    
    yield # This tells FastAPI to pause here and let the server run
    
    # --- SHUTDOWN PHASE ---
    print("Server shutting down...")

# Pass the lifespan into the FastAPI app
app = FastAPI(
    title="AI Video Knowledge Extractor - Monolith Core",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router)

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "engine": "ONLINE"}