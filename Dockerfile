# ========================================================
# Free AI Explainer Video Generator - Production Dockerfile
# Multi-stage build: React Frontend + FastAPI Backend + Manim + FFmpeg
# ========================================================

# --------------------------------------------------------
# Stage 1: Frontend Build
# --------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --------------------------------------------------------
# Stage 2: Python Application & Media Engine
# --------------------------------------------------------
FROM python:3.11-slim

# Prevent interactive prompts and set Python flags
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies: FFmpeg, Cairo, Pango, and build tools for Manim
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libgl1 \
    pkg-config \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Copy built frontend assets from Stage 1 into the backend container
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Pre-create storage directory structure
RUN python -c "from config import config; config.init_directories()"

# Expose backend & frontend port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start FastAPI server
CMD ["python", "server.py"]
