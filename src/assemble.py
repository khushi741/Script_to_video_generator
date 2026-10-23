"""
Video Assembly & Manim Rendering Engine.
Handles scene rendering (templates + optional freeform code), audio-video muxing,
burned-in subtitle rendering, and final multi-scene MP4 stitching via FFmpeg.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import yaml

from src.schemas import SceneScript
from core.logger import setup_logger

logger = setup_logger("assemble")


class VideoAssembler:
    """Renders Manim scenes, syncs audio, burns subtitles, and concatenates final video."""

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path or Path(__file__).resolve().parent.parent / "config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "animation": {
                    "quality_flag": "-qm",
                    "mode": "templates",
                },
                "subtitles": {"enabled": True},
            }

        self.quality_flag = self.config.get("animation", {}).get("quality_flag", "-qm")
        self.mode = self.config.get("animation", {}).get("mode", "templates")
        self._verify_ffmpeg()

    @staticmethod
    def get_ffmpeg_binary() -> Optional[str]:
        """Finds FFmpeg executable from system PATH or imageio_ffmpeg bundle."""
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

    @classmethod
    def _verify_ffmpeg(cls):
        """Checks if ffmpeg is accessible on PATH or bundled via imageio_ffmpeg."""
        ffmpeg_bin = cls.get_ffmpeg_binary()
        if not ffmpeg_bin:
            logger.error("FFmpeg was NOT found on your system PATH or imageio_ffmpeg! Video assembly will fail.")
            logger.info("Windows: winget install Gyan.FFmpeg | Mac: brew install ffmpeg | Linux: apt install ffmpeg")
        else:
            logger.info(f"FFmpeg engine active: {ffmpeg_bin}")

    def render_scene(
        self,
        scene: SceneScript,
        target_duration: float,
        output_dir: Path,
        scene_index: int,
    ) -> Tuple[Path, bool, str]:
        """
        Renders a single scene using its designated Manim template.
        Returns: (rendered_mp4_path, success_boolean, error_or_log_message)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        scene_mp4 = output_dir / f"scene_{scene_index}_{scene.visual_type}.mp4"

        logger.info(f"Rendering Scene {scene_index} ({scene.visual_type}, target duration: {target_duration:.2f}s)")

        # Generate Python script for the Manim scene
        runner_script = output_dir / f"runner_scene_{scene_index}.py"
        self._write_scene_runner_script(scene, target_duration, runner_script)

        # Execute Manim subprocess
        success, message = self._execute_manim(runner_script, "GeneratedScene", scene_mp4)

        if not success:
            logger.warning(f"Scene {scene_index} primary template failed: {message}. Triggering FallbackScene...")
            # Fallback execution
            fallback_script = output_dir / f"fallback_runner_{scene_index}.py"
            self._write_fallback_script(scene, target_duration, fallback_script)
            fb_success, fb_message = self._execute_manim(fallback_script, "SafeFallbackScene", scene_mp4)
            return scene_mp4, fb_success, f"Used fallback: {fb_message}"

        return scene_mp4, True, "Render successful"

    def _write_scene_runner_script(self, scene: SceneScript, target_duration: float, file_path: Path):
        """Builds a standalone executable Manim script invoking the template class."""
        visual_type = scene.visual_type
        visual_data = scene.visual_data

        class_map = {
            "title": ("src.templates.title_scene", "TitleScene"),
            "bullets": ("src.templates.bullets_scene", "BulletsScene"),
            "equation": ("src.templates.equation_scene", "EquationScene"),
            "graph": ("src.templates.graph_scene", "GraphScene"),
            "diagram": ("src.templates.diagram_scene", "DiagramScene"),
        }

        module_path, class_name = class_map.get(visual_type, ("src.templates.fallback_scene", "FallbackScene"))

        code = f"""
import sys
from pathlib import Path
sys.path.insert(0, r"{str(Path(__file__).resolve().parent.parent)}")

from {module_path} import {class_name}

class GeneratedScene({class_name}):
    def __init__(self, **kwargs):
        super().__init__(
            visual_data={repr(visual_data)},
            target_duration={float(target_duration)},
            **kwargs
        )
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

    def _write_fallback_script(self, scene: SceneScript, target_duration: float, file_path: Path):
        """Creates a minimal fallback runner script."""
        fallback_data = {
            "title": scene.title,
            "summary": scene.narration[:200]
        }
        code = f"""
import sys
from pathlib import Path
sys.path.insert(0, r"{str(Path(__file__).resolve().parent.parent)}")

from src.templates.fallback_scene import FallbackScene

class SafeFallbackScene(FallbackScene):
    def __init__(self, **kwargs):
        super().__init__(
            visual_data={repr(fallback_data)},
            target_duration={float(target_duration)},
            **kwargs
        )
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

    def _execute_manim(self, script_path: Path, scene_class: str, target_output_mp4: Path) -> Tuple[bool, str]:
        """Runs Manim via CLI and renames the output video to target path."""
        manim_bin = shutil.which("manim")
        if not manim_bin:
            return False, "Manim CLI executable not found on PATH. Install Manim via 'pip install manim' and ensure it is on PATH."

        media_dir = script_path.parent / "manim_media"
        cmd = [
            manim_bin,
            self.quality_flag,
            "--media_dir", str(media_dir),
            str(script_path),
            scene_class,
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        except FileNotFoundError:
            return False, "Manim binary not found during execution."
        except subprocess.TimeoutExpired:
            return False, "Manim render timed out after 300 seconds."

        if result.returncode != 0:
            return False, result.stderr[-500:]

        # Locate generated MP4 in manim_media
        found_mp4 = list(media_dir.glob(f"**/{scene_class}.mp4"))
        if not found_mp4:
            return False, "Render finished with code 0 but output MP4 was not found."

        shutil.copyfile(found_mp4[0], target_output_mp4)
        return True, "Success"

    def mux_scene_audio_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        srt_path: Optional[Path] = None,
    ) -> Path:
        """Merges a single scene video with its audio and optional subtitles."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg_bin = self.get_ffmpeg_binary()
        if not ffmpeg_bin:
            logger.error("FFmpeg not found on system PATH. Cannot mux audio and video.")
            if video_path.exists():
                shutil.copyfile(video_path, output_path)
            return output_path

        # Build FFmpeg command
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
        ]

        # Subtitles filter if present
        if srt_path and srt_path.exists() and self.config.get("subtitles", {}).get("enabled", True):
            # Escape path for FFmpeg subtitles filter
            escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
            cmd.extend([
                "-vf",
                f"subtitles='{escaped_srt}':force_style='FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'",
            ])
            cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-shortest", str(output_path)])
        else:
            cmd.extend(["-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path)])

        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                logger.warning(f"Subtitle muxing failed ({res.stderr[:200]}). Falling back to simple audio-video mux.")
                # Fallback without subtitle filter
                subprocess.run(
                    [ffmpeg_bin, "-y", "-i", str(video_path), "-i", str(audio_path), "-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception as e:
            logger.error(f"Error during audio-video muxing: {str(e)}")
            if video_path.exists() and not output_path.exists():
                shutil.copyfile(video_path, output_path)

        return output_path

    def concatenate_scenes(self, scene_mp4s: List[Path], final_output_mp4: Path) -> Path:
        """Stitches all individual scene MP4s into the final video file."""
        final_output_mp4 = Path(final_output_mp4)
        final_output_mp4.parent.mkdir(parents=True, exist_ok=True)

        if not scene_mp4s:
            raise ValueError("No scene MP4s provided for concatenation.")

        ffmpeg_bin = self.get_ffmpeg_binary()
        if not ffmpeg_bin:
            logger.error("FFmpeg not found on system PATH. Cannot concatenate scenes.")
            if scene_mp4s[0].exists():
                shutil.copyfile(scene_mp4s[0], final_output_mp4)
            return final_output_mp4

        concat_list_file = final_output_mp4.parent / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in scene_mp4s:
                norm_p = str(p.resolve()).replace("\\", "/")
                f.write(f"file '{norm_p}'\n")

        logger.info(f"Concatenating {len(scene_mp4s)} scenes into {final_output_mp4.name}...")

        cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(final_output_mp4),
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                logger.warning("Fast stream copy concatenation failed. Re-encoding cleanly with libx264...")
                # Re-encode fallback if stream copy has PTS/timestamp mismatch
                subprocess.run(
                    [
                        ffmpeg_bin, "-y",
                        "-f", "concat", "-safe", "0",
                        "-i", str(concat_list_file),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac",
                        str(final_output_mp4),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception as e:
            logger.error(f"Error during video concatenation: {str(e)}")
            if scene_mp4s and scene_mp4s[0].exists() and not final_output_mp4.exists():
                shutil.copyfile(scene_mp4s[0], final_output_mp4)
        finally:
            concat_list_file.unlink(missing_ok=True)

        logger.info(f"Final video generated successfully: {final_output_mp4}")
        return final_output_mp4
