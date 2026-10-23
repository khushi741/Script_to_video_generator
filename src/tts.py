"""
Text-To-Speech (TTS) Engine.
Supports edge-tts (English & Hindi) with Piper offline fallback.
Generates audio files per scene and returns precise duration.
"""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import yaml

# Compatible import across MoviePy 1.x and MoviePy 2.x
try:
    from moviepy.editor import AudioFileClip
except (ImportError, ModuleNotFoundError):
    try:
        from moviepy import AudioFileClip
    except (ImportError, ModuleNotFoundError):
        try:
            from moviepy.audio.io.AudioFileClip import AudioFileClip
        except (ImportError, ModuleNotFoundError):
            AudioFileClip = None

from core.logger import setup_logger

logger = setup_logger("tts_engine")


class TTSEngine:
    """Manages scene narration synthesis with multi-language and fallback support."""

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path or Path(__file__).resolve().parent.parent / "config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f).get("tts", {})
        else:
            self.config = {
                "default_engine": "edge-tts",
                "default_language": "en",
                "voices": {
                    "en": "en-US-AriaNeural",
                    "hi": "hi-IN-SwaraNeural",
                },
                "rate": "+0%",
                "volume": "+0%",
            }

        self.voices = self.config.get("voices", {
            "en": "en-US-AriaNeural",
            "hi": "hi-IN-SwaraNeural",
        })

    def synthesize(
        self,
        text: str,
        output_path: Path,
        language: str = "en",
        voice: Optional[str] = None,
    ) -> Tuple[Path, float]:
        """
        Synthesizes speech for the given text.
        Returns: (output_file_path, duration_seconds)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        chosen_voice = voice or self.voices.get(language, self.voices.get("en", "en-US-AriaNeural"))
        clean_text = text.strip()

        logger.info(f"Synthesizing TTS ({language}, voice: {chosen_voice}) -> {output_path.name}")

        # 1. Try edge-tts first
        try:
            asyncio.run(self._synthesize_edge_tts(clean_text, str(output_path), chosen_voice))
            duration = self._get_audio_duration(output_path)
            logger.info(f"edge-tts synthesized successfully: {output_path.name} ({duration:.2f}s)")
            return output_path, duration
        except Exception as e:
            logger.warning(f"edge-tts failed ({str(e)}). Attempting Piper offline fallback...")

        # 2. Try Piper offline fallback
        try:
            self._synthesize_piper(clean_text, output_path)
            duration = self._get_audio_duration(output_path)
            logger.info(f"Piper synthesized successfully: {output_path.name} ({duration:.2f}s)")
            return output_path, duration
        except Exception as piper_err:
            logger.error(f"Piper fallback failed ({str(piper_err)}). Generating silent emergency audio.")

        # 3. Ultimate Fallback: Silent audio clip proportional to word count
        duration = self._create_silent_audio(clean_text, output_path)
        return output_path, duration

    async def _synthesize_edge_tts(self, text: str, output_file: str, voice: str):
        """Asynchronously runs edge-tts."""
        import edge_tts
        rate = self.config.get("rate", "+0%")
        volume = self.config.get("volume", "+0%")

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
        )
        await communicate.save(output_file)

    def _synthesize_piper(self, text: str, output_path: Path):
        """Runs offline Piper TTS executable if available in PATH or Python package."""
        piper_bin = shutil.which("piper")
        if not piper_bin:
            raise RuntimeError("Piper executable not found in system PATH.")

        wav_path = output_path.with_suffix(".wav")
        proc = subprocess.Popen(
            [piper_bin, "--output_file", str(wav_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=text)
        if proc.returncode != 0:
            raise RuntimeError(f"Piper error: {stderr}")

        # If desired output is mp3, convert with ffmpeg
        if output_path.suffix.lower() == ".mp3":
            ffmpeg_exe = self._get_ffmpeg()
            if ffmpeg_exe:
                subprocess.run(
                    [ffmpeg_exe, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", str(output_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            wav_path.unlink(missing_ok=True)

    @staticmethod
    def _get_ffmpeg() -> Optional[str]:
        bin_path = shutil.which("ffmpeg")
        if bin_path:
            return bin_path
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and Path(exe).exists():
                return exe
        except Exception:
            pass
        return None

    @staticmethod
    def _get_audio_duration(file_path: Path) -> float:
        """Retrieves exact audio duration in seconds with robust fallbacks."""
        if AudioFileClip:
            clip = None
            try:
                clip = AudioFileClip(str(file_path))
                return float(clip.duration)
            except Exception:
                pass
            finally:
                if clip:
                    clip.close()

        # Fallback 1: Use ffprobe if available
        ffprobe_bin = shutil.which("ffprobe")
        if ffprobe_bin:
            try:
                res = subprocess.run(
                    [
                        ffprobe_bin, "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                        str(file_path)
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return float(res.stdout.strip())
            except Exception:
                pass

        # Fallback 2: Check for WAV file header
        if file_path.suffix.lower() == ".wav":
            try:
                import wave
                with wave.open(str(file_path), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate > 0:
                        return round(frames / float(rate), 2)
            except Exception:
                pass

        # Default fallback: safe 5.0s estimation
        return 5.0

    @staticmethod
    def _create_silent_audio(text: str, output_path: Path) -> float:
        """Creates a silent audio placeholder if TTS fails entirely."""
        # Estimate: ~130 words per minute -> ~2.2 words per second
        word_count = len(text.split())
        est_duration = max(3.0, round(word_count / 2.2, 2))

        # Generate silent audio with ffmpeg if available
        ffmpeg_exe = TTSEngine._get_ffmpeg()
        if ffmpeg_exe:
            subprocess.run(
                [
                    ffmpeg_exe, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", str(est_duration), "-q:a", "9", "-acodec", "libmp3lame", str(output_path)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        return est_duration
