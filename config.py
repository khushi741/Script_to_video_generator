import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent

class PathConfig(BaseModel):
    STORAGE_DIR: Path = BASE_DIR / "storage"
    RAW_UPLOADS: Path = STORAGE_DIR / "raw_uploads"
    AUDIO_DIR: Path = STORAGE_DIR / "audio"
    VIDEO_SCENES_DIR: Path = STORAGE_DIR / "video_scenes"
    SUBTITLES_DIR: Path = STORAGE_DIR / "subtitles"
    OUTPUT_DIR: Path = STORAGE_DIR / "output"

class LLMConfig(BaseModel):
    HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")  # Fallbacks: qwen2.5:7b, gemma2:9b
    TEMPERATURE: float = 0.2
    MAX_RETRIES: int = 3

class TTSConfig(BaseModel):
    DEFAULT_VOICE: str = "en-US-ChristopherNeural"  # Hindi: hi-IN-MadhurNeural / hi-IN-SwaraNeural
    FALLBACK_ENGINE: str = "piper"  # Offline fallback
    RATE: str = "+0%"
    VOLUME: str = "+0%"

class VideoConfig(BaseModel):
    WIDTH: int = 1920
    HEIGHT: int = 1080
    FPS: int = 30
    MANIM_QUALITY: str = "medium_quality"  # low_quality (-ql) for fast preview, medium (-qm), high (-qh)

class Config(BaseModel):
    PATHS: PathConfig = PathConfig()
    LLM: LLMConfig = LLMConfig()
    TTS: TTSConfig = TTSConfig()
    VIDEO: VideoConfig = VideoConfig()

    def init_directories(self):
        for path in [
            self.PATHS.STORAGE_DIR,
            self.PATHS.RAW_UPLOADS,
            self.PATHS.AUDIO_DIR,
            self.PATHS.VIDEO_SCENES_DIR,
            self.PATHS.SUBTITLES_DIR,
            self.PATHS.OUTPUT_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)

config = Config()
config.init_directories()
