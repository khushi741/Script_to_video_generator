# 🎬 Free AI Explainer Video Generator

An autonomous, 100% free and open-source system that turns study notes or chapter PDFs into high-quality, narrated, animated explainer videos (`.mp4`) with synchronized speech and burned-in subtitles.

Designed to run smoothly on standard laptops (**8–16 GB RAM, no GPU required**).

---

## 🏗️ Architecture & Pipeline

```text
[ Study Notes / PDF ]
         ↓ (PyMuPDF)
1. Ingest & Sanitize Text
         ↓ (Ollama Llama 3.1 8B)
2. Generate Strict JSON Script (4-8 Scenes)
         ↓
   ┌──────────────────────────────────────────────┐
   │           Per-Scene Parallel Sync            │
   │                                              │
   │ 3. Narration (edge-tts / Piper fallback)     │
   │ 4. Subtitle Timestamps (faster-whisper int8) │
   │ 5. Visual Render (Manim Community Edition)   │
   └──────────────────────────────────────────────┘
         ↓
6. FFmpeg Mux & Multi-Scene Concatenation
         ↓
7. Quality Assurance & Hallucination Audit (Ollama)
         ↓
[ Final Explainer MP4 + Subtitles + Quality Report ]
```

---

## 🛠️ Tech Stack (100% Free & Open Source)

- **LLM Engine:** [Ollama](https://ollama.com) (`llama3.1:8b`, `qwen2.5:7b`, or `gemma2:9b`). Zero paid API tokens.
- **Animation Engine:** [Manim Community Edition](https://www.manim.community/) with dynamic timing synchronization.
- **Text-To-Speech:** `edge-tts` (Natural neural voices in English and Hindi) + `piper-tts` offline fallback.
- **Subtitles & Word Timestamps:** `faster-whisper` (Quantized `int8` CPU inference, ~1.5 GB RAM).
- **Video Assembly:** `ffmpeg` + `moviepy`.
- **Document Ingestion:** `PyMuPDF` (`fitz`).
- **User Interface:** `Streamlit`.

---

## 🚀 Installation Guide

### Step 1: System Tools

#### Windows:
```powershell
# 1. Install FFmpeg
winget install Gyan.FFmpeg

# 2. Install Ollama from https://ollama.com
# Then in PowerShell pull the default model:
ollama pull llama3.1:8b
# (For 8 GB RAM laptops, qwen2.5:7b is recommended):
# ollama pull qwen2.5:7b
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install -y ffmpeg libpango1.0-dev libcairo2-dev
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
```

#### macOS:
```bash
brew install ffmpeg cairo pango
brew install --cask ollama
ollama pull llama3.1:8b
```

---

### Step 2: Python Environment & Dependencies

```bash
cd d:\project\Script_to_video_generator
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🏃 How to Run & Deploy

### Option A: Docker Deployment (Production Ready)

Deploy the entire stack (React UI + FastAPI Backend + FFmpeg + Manim + Ollama) with one command:
```bash
docker compose up --build
```
- App + Studio UI: **`http://localhost:8000`**
- Ollama Daemon: **`http://localhost:11434`**

---

### Option B: Unified Studio Server (Zero Configuration)

The FastAPI server now automatically serves the pre-built React Studio UI directly:
```bash
python server.py
# Or double-click start_server.bat on Windows
```
Open **`http://localhost:8000`** in your browser.

---

### Option C: Frontend Development Mode (Hot Reload)

If you are developing frontend components:
```bash
# Terminal 1: Backend with dev reload
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: React Dev Server
cd frontend
npm run dev
```
Open your browser at **`http://localhost:3000`**.

---

## 🧪 Automated Test Suite

Run the full automated test suite (schemas, text ingestion, timestamp alignment, and API lifecycle):
```bash
pytest tests/ -v
```

### Option D: Command Line Interface (CLI)

#### Run Default Demo (Newton's Second Law):
```bash
python src/pipeline.py --topic "Newton's Second Law (F = ma) for Class 10 students" --language en
```

#### Run with Custom Text Notes:
```bash
python src/pipeline.py --topic "Photosynthesis" --text "Plants convert light energy, carbon dioxide, and water into chemical energy in the form of glucose..." --language en
```

#### Run with a Chapter PDF:
```bash
python src/pipeline.py --topic "Thermodynamics" --pdf "storage/raw_uploads/physics_ch1.pdf" --language en
```

---

## 🧪 Automated Evaluation Benchmark

Run the automated evaluation suite across 5 sample topics:
```bash
python eval/run_eval.py
```
Outputs a full summary table and metrics file under `storage/eval/eval_summary_*.json`.

---

## 🔧 Troubleshooting & Known Failure Points

| Failure / Error | Cause | Built-in Resolution |
| :--- | :--- | :--- |
| **`FileNotFoundError: ffmpeg`** | FFmpeg is not installed or not added to your system `PATH`. | Install FFmpeg via `winget install Gyan.FFmpeg` (Windows) or `brew install ffmpeg` (Mac) and restart your terminal. |
| **LaTeX missing (`MathTex` error)** | Manim defaults to LaTeX for math, but standard laptops don't have 4 GB TeX installed. | **Zero-Crash Design:** Our `equation_scene.py` automatically detects when LaTeX is absent and seamlessly falls back to high-resolution Unicode text formatting. |
| **Ollama connection refused (`11434`)** | Ollama background server is not running. | Run `ollama serve` in a separate terminal window before launching the app. |
| **`edge-tts` network error** | Machine is offline or Microsoft server blocked request. | The pipeline automatically catches the network error and falls back to **Piper offline TTS** (or generates duration-aligned silent track). |
| **Whisper slow or high RAM usage** | Default Whisper uses heavy PyTorch FP32 models. | We use `faster-whisper` configured specifically with `device="cpu"` and `compute_type="int8"`, keeping RAM under 1.5 GB. |

---

## ✅ First-Time Verification Checklist

Run these commands in order to confirm your setup:
1. `ffmpeg -version` $\rightarrow$ Confirms FFmpeg is on PATH.
2. `ollama list` $\rightarrow$ Confirms Ollama daemon is active and `llama3.1:8b` is pulled.
3. `manim --version` $\rightarrow$ Confirms Manim Community Edition is installed.
4. `python src/pipeline.py --topic "Newton's Second Law (F = ma) for Class 10 students"` $\rightarrow$ Tests end-to-end video creation.
5. `streamlit run app.py` $\rightarrow$ Launches web interface.
