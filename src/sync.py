"""
Audio-Visual Synchronization & Subtitle Generation module using faster-whisper.
Extracts word-level timestamps, builds .srt subtitles, and calculates exact scene timing alignment.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from faster_whisper import WhisperModel

from core.logger import setup_logger

logger = setup_logger("sync_engine")


class SyncEngine:
    """Handles speech-to-text timestamp alignment and subtitle generation."""

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path or Path(__file__).resolve().parent.parent / "config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f).get("subtitles", {})
        else:
            self.config = {"whisper_model": "base"}

        model_size = self.config.get("whisper_model", "base")
        logger.info(f"Initializing faster-whisper (model: '{model_size}', device: cpu, compute_type: int8)...")

        # Configured strictly for CPU laptops (8-16GB RAM)
        self.whisper = WhisperModel(model_size, device="cpu", compute_type="int8")

    def generate_subtitles_for_audio(
        self,
        audio_path: Path,
        output_srt_path: Path,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Transcribes audio with word-level timestamps and writes an SRT subtitle file.
        Returns list of segment dictionaries with start, end, and text.
        """
        output_srt_path = Path(output_srt_path)
        output_srt_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Transcribing audio for subtitles: {audio_path.name}")
        segments, info = self.whisper.transcribe(
            str(audio_path),
            language=language if language in ["en", "hi"] else None,
            word_timestamps=True,
            vad_filter=True,
        )

        segment_data: List[Dict[str, Any]] = []
        srt_lines: List[str] = []
        counter = 1

        for segment in segments:
            seg_info = {
                "id": counter,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            segment_data.append(seg_info)

            # Build SRT block
            start_srt = self._format_timestamp(segment.start)
            end_srt = self._format_timestamp(segment.end)
            srt_lines.append(f"{counter}\n{start_srt} --> {end_srt}\n{segment.text.strip()}\n")
            counter += 1

        with open(output_srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        logger.info(f"Generated {len(segment_data)} subtitle segments -> {output_srt_path.name}")
        return segment_data

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Converts float seconds to SRT time format: 00:00:00,000"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milli = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{milli:03d}"

    @staticmethod
    def calculate_sync_parameters(audio_duration: float, visual_complexity: int = 3) -> Dict[str, float]:
        """
        Calculates optimal run_time and wait duration for Manim animations
        to ensure video clip matches narration duration down to milliseconds.
        """
        # Ensure a minimum safety duration of 3 seconds
        safe_duration = max(3.0, float(audio_duration))

        # Animation takes up to 70% of narration time, remaining 30% is hold
        active_anim_budget = safe_duration * 0.70
        run_time_per_item = max(0.6, active_anim_budget / visual_complexity)
        total_anim_time = run_time_per_item * visual_complexity
        hold_time = max(0.5, safe_duration - total_anim_time)

        return {
            "target_duration": safe_duration,
            "run_time_per_item": run_time_per_item,
            "hold_time": hold_time,
        }
