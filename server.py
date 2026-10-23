"""
FastAPI Backend Server for React Frontend.
Provides endpoints for video generation jobs, real-time progress polling,
PDF uploading, video streaming, quality report inspection, and static SPA serving.
Includes SQLite-backed persistent job store and graceful error handling.
"""

import os
import sys
import uuid
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import VideoGenerationPipeline
from core.logger import setup_logger

logger = setup_logger("fastapi_server")

app = FastAPI(
    title="Free AI Explainer Video Generator API",
    version="1.0.0",
    description="Backend API powering the React Explainer Video Generator Studio",
)

# CORS configuration
cors_env = os.getenv("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobStore:
    """Thread-safe persistent job storage using SQLite with memory cache."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        topic TEXT,
                        status TEXT,
                        progress REAL,
                        message TEXT,
                        result TEXT,
                        error TEXT,
                        created_at REAL,
                        updated_at REAL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def _load_cache(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100")
                for row in cursor.fetchall():
                    self._cache[row["job_id"]] = {
                        "job_id": row["job_id"],
                        "topic": row["topic"],
                        "status": row["status"],
                        "progress": row["progress"],
                        "message": row["message"],
                        "result": json.loads(row["result"]) if row["result"] else None,
                        "error": row["error"],
                    }
            finally:
                conn.close()

    def create_job(self, job_id: str, topic: str):
        now = time.time()
        job_data = {
            "job_id": job_id,
            "topic": topic,
            "status": "running",
            "progress": 0.05,
            "message": "Initializing pipeline...",
            "result": None,
            "error": None,
        }
        with self._lock:
            self._cache[job_id] = job_data
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs (job_id, topic, status, progress, message, result, error, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (job_id, topic, "running", 0.05, "Initializing pipeline...", None, None, now, now),
                )
                conn.commit()
            finally:
                conn.close()
        return job_data

    def update_progress(self, job_id: str, percent: float, message: str):
        with self._lock:
            if job_id in self._cache:
                self._cache[job_id]["progress"] = round(percent, 2)
                self._cache[job_id]["message"] = message

            conn = self._get_connection()
            try:
                conn.execute(
                    "UPDATE jobs SET progress = ?, message = ?, updated_at = ? WHERE job_id = ?",
                    (round(percent, 2), message, time.time(), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        result_json = json.dumps(result)
        with self._lock:
            if job_id in self._cache:
                self._cache[job_id]["status"] = "completed"
                self._cache[job_id]["progress"] = 1.0
                self._cache[job_id]["message"] = "Video generation complete!"
                self._cache[job_id]["result"] = result

            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    UPDATE jobs SET status = 'completed', progress = 1.0, message = 'Video generation complete!',
                    result = ?, updated_at = ? WHERE job_id = ?
                    """,
                    (result_json, time.time(), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def fail_job(self, job_id: str, error_msg: str):
        with self._lock:
            if job_id in self._cache:
                self._cache[job_id]["status"] = "failed"
                self._cache[job_id]["message"] = "Error during generation"
                self._cache[job_id]["error"] = error_msg

            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    UPDATE jobs SET status = 'failed', message = 'Error during generation',
                    error = ?, updated_at = ? WHERE job_id = ?
                    """,
                    (error_msg, time.time(), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if job_id in self._cache:
                return self._cache[job_id]

            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    job = {
                        "job_id": row["job_id"],
                        "topic": row["topic"],
                        "status": row["status"],
                        "progress": row["progress"],
                        "message": row["message"],
                        "result": json.loads(row["result"]) if row["result"] else None,
                        "error": row["error"],
                    }
                    self._cache[job_id] = job
                    return job
            finally:
                conn.close()
        return None


# Initialize persistent job storage in storage/jobs.db
db_file = Path(__file__).resolve().parent / "storage" / "jobs.db"
job_store = JobStore(db_file)


class GenerateRequest(BaseModel):
    topic: str
    input_text: Optional[str] = None
    pdf_filename: Optional[str] = None
    language: str = "en"
    target_audience: str = "Class 10 students"


def _run_pipeline_background(job_id: str, req: GenerateRequest, pdf_path: Optional[str]):
    """Executes the pipeline in a background thread while updating the job status."""
    logger.info(f"Starting background job {job_id} for topic: '{req.topic}'")

    def progress_callback(msg: str, percent: float):
        job_store.update_progress(job_id, percent, msg)

    try:
        pipeline = VideoGenerationPipeline()
        res = pipeline.run(
            topic=req.topic,
            input_text=req.input_text,
            pdf_path=pdf_path,
            language=req.language,
            target_audience=req.target_audience,
            progress_callback=progress_callback,
        )
        job_store.complete_job(job_id, res)
        logger.info(f"Job {job_id} finished successfully!")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        job_store.fail_job(job_id, str(e))


@app.get("/api/health")
def health_check():
    """Returns system status including Ollama, FFmpeg, and Manim checks."""
    import shutil
    import requests

    ffmpeg_available = bool(shutil.which("ffmpeg"))
    manim_available = bool(shutil.which("manim"))
    ollama_available = False

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        r = requests.get(f"{ollama_host}/api/tags", timeout=3)
        ollama_available = (r.status_code == 200)
    except Exception:
        pass

    return {
        "status": "online",
        "ffmpeg_installed": ffmpeg_available,
        "manim_installed": manim_available,
        "ollama_running": ollama_available,
    }


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Handles PDF file uploads and saves to raw_uploads directory."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    upload_dir = Path(__file__).resolve().parent / "storage" / "raw_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{uuid.uuid4().hex[:8]}_{file.filename}"
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"Saved uploaded PDF: {file_path.name}")
    return {
        "status": "success",
        "filename": file_path.name,
        "path": str(file_path),
        "size_bytes": len(contents),
    }


@app.post("/api/generate")
def start_generation(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Initializes a new video generation job and returns the job ID."""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic is required.")

    job_id = f"job_{uuid.uuid4().hex[:10]}"

    pdf_full_path = None
    if req.pdf_filename:
        upload_dir = Path(__file__).resolve().parent / "storage" / "raw_uploads"
        candidate = upload_dir / req.pdf_filename
        if candidate.exists():
            pdf_full_path = str(candidate)

    job_store.create_job(job_id, req.topic)

    # Run in separate thread to prevent blocking FastAPI async event loop
    thread = threading.Thread(
        target=_run_pipeline_background,
        args=(job_id, req, pdf_full_path),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "job_id": job_id}


@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    """Polls real-time progress of a video generation task."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/video/{job_id}")
def get_video_file(job_id: str):
    """Serves the generated MP4 video file with streaming headers."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["status"] != "completed" or not job.get("result"):
        raise HTTPException(status_code=400, detail="Video is not ready yet.")

    video_path = Path(job["result"]["video_path"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )


@app.get("/api/report/{job_id}")
def get_quality_report(job_id: str):
    """Returns the full quality and hallucination report JSON."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.get("result"):
        raise HTTPException(status_code=400, detail="Report not ready yet.")

    return job["result"].get("quality_report", {})


@app.post("/api/cleanup")
def cleanup_storage(max_age_hours: int = 48):
    """Cleans up temporary audio, scenes, and subtitles older than max_age_hours."""
    storage_root = Path(__file__).resolve().parent / "storage"
    cutoff = time.time() - (max_age_hours * 3600)
    cleaned_files = 0

    for sub_dir in ["audio", "scenes", "subtitles"]:
        folder = storage_root / sub_dir
        if folder.exists():
            for p in folder.glob("*"):
                try:
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        p.unlink()
                        cleaned_files += 1
                except Exception:
                    pass

    return {"status": "success", "files_removed": cleaned_files}


# Mount production React SPA if frontend/dist exists
dist_dir = Path(__file__).resolve().parent / "frontend" / "dist"
if dist_dir.exists():
    logger.info(f"Serving built React frontend from {dist_dir}")
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target_file = dist_dir / full_path
        if full_path and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(dist_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload_flag = os.getenv("DEV_MODE", "false").lower() in ("true", "1")
    logger.info(f"Starting server on http://{host}:{port} (reload={reload_flag})")
    uvicorn.run("server:app", host=host, port=port, reload=reload_flag)
