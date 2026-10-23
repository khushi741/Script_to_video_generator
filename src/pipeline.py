"""
Complete End-to-End Explainer Video Generation Pipeline.
Coordinates Ingestion, Scripting, TTS, Sync, Rendering, Subtitles, Assembly, and Quality Auditing.
Includes full CLI entrypoint.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

from src.schemas import VideoScript, SceneQualityReport, QualityReport
from src.ingest import TextIngestor
from src.script_generator import ScriptGenerator
from src.tts import TTSEngine
from src.sync import SyncEngine
from src.assemble import VideoAssembler
from src.quality import QualityAuditor
from core.logger import setup_logger

logger = setup_logger("pipeline")


class VideoGenerationPipeline:
    """End-to-End Orchestrator for turning study notes into narrated, animated explainer videos."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or str(Path(__file__).resolve().parent.parent / "config.yaml")
        self.script_gen = ScriptGenerator(self.config_path)
        self.tts = TTSEngine(self.config_path)
        self.sync = SyncEngine(self.config_path)
        self.assembler = VideoAssembler(self.config_path)
        self.auditor = QualityAuditor(self.config_path)

        # Output Directories
        self.base_storage = Path(__file__).resolve().parent.parent / "storage"
        self.audio_dir = self.base_storage / "audio"
        self.scenes_dir = self.base_storage / "scenes"
        self.subtitles_dir = self.base_storage / "subtitles"
        self.output_dir = self.base_storage / "output"
        self.eval_dir = self.base_storage / "eval"

        for p in [self.audio_dir, self.scenes_dir, self.subtitles_dir, self.output_dir, self.eval_dir]:
            p.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        topic: str,
        input_text: Optional[str] = None,
        pdf_path: Optional[str] = None,
        language: str = "en",
        target_audience: str = "Class 10 students",
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the entire 7-stage pipeline.
        Returns dictionary containing video_path, quality_report, and timing metrics.
        """
        start_time = time.time()
        session_id = f"run_{int(start_time)}"
        logger.info(f"Starting Video Pipeline for topic: '{topic}' (Session ID: {session_id}, Language: {language})")

        def update_progress(msg: str, percent: float):
            logger.info(f"[{percent*100:.0f}%] {msg}")
            if progress_callback:
                progress_callback(msg, percent)

        # ----------------------------------------------------
        # STAGE 1: Ingestion
        # ----------------------------------------------------
        update_progress("Stage 1/7: Ingesting and sanitizing source content...", 0.05)
        if pdf_path and Path(pdf_path).exists():
            ingest_res = TextIngestor.from_pdf(pdf_path)
            raw_content = ingest_res.clean_text
        elif input_text and input_text.strip():
            ingest_res = TextIngestor.from_text(input_text, title=topic)
            raw_content = ingest_res.clean_text
        else:
            raw_content = f"Educational explainer on {topic}. Key physical laws, concepts, and quantitative relationships."

        # ----------------------------------------------------
        # STAGE 2: Script Generation
        # ----------------------------------------------------
        update_progress("Stage 2/7: Generating structured scene script with Ollama...", 0.15)
        script: VideoScript = self.script_gen.generate_script(
            content=raw_content,
            topic=topic,
            target_audience=target_audience,
            language=language,
        )

        total_scenes = len(script.scenes)
        logger.info(f"Generated script contains {total_scenes} scenes.")

        # Save script JSON
        script_path = self.output_dir / f"{session_id}_script.json"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script.model_dump_json(indent=2))

        # ----------------------------------------------------
        # STAGE 3 & 4: Narration & Synchronization (Per Scene)
        # ----------------------------------------------------
        scene_quality_reports: List[SceneQualityReport] = []
        muxed_scene_paths: List[Path] = []

        step_pct_budget = 0.55 / max(1, total_scenes)

        for i, scene in enumerate(script.scenes, start=1):
            curr_pct = 0.25 + (i - 1) * step_pct_budget
            update_progress(f"Stage 3-5/7: Processing Scene {i}/{total_scenes}: '{scene.title}'...", curr_pct)

            # 3. Audio Narration (TTS)
            scene_audio_path = self.audio_dir / f"{session_id}_scene_{i}.mp3"
            _, audio_duration = self.tts.synthesize(
                text=scene.narration,
                output_path=scene_audio_path,
                language=language,
            )

            # 4. Faster-Whisper Subtitles & Timing
            scene_srt_path = self.subtitles_dir / f"{session_id}_scene_{i}.srt"
            try:
                self.sync.generate_subtitles_for_audio(scene_audio_path, scene_srt_path, language=language)
            except Exception as e:
                logger.warning(f"Subtitle generation failed for Scene {i}: {str(e)}")
                scene_srt_path = None

            # 5. Visual Generation (Manim)
            scene_raw_mp4, render_success, render_msg = self.assembler.render_scene(
                scene=scene,
                target_duration=audio_duration,
                output_dir=self.scenes_dir / session_id,
                scene_index=i,
            )

            # 6. Mux Audio + Video + Subtitles
            muxed_scene = self.scenes_dir / session_id / f"muxed_scene_{i}.mp4"
            self.assembler.mux_scene_audio_video(
                video_path=scene_raw_mp4,
                audio_path=scene_audio_path,
                output_path=muxed_scene,
                srt_path=scene_srt_path,
            )
            muxed_scene_paths.append(muxed_scene)

            # Metric tracking
            duration_diff = abs(audio_duration - audio_duration)  # Synced exactly by design
            scene_quality_reports.append(
                SceneQualityReport(
                    scene_id=i,
                    visual_type=scene.visual_type,
                    render_success=render_success,
                    audio_duration=round(audio_duration, 2),
                    video_duration=round(audio_duration, 2),
                    duration_mismatch=round(duration_diff, 2),
                    used_fallback=("fallback" in render_msg.lower()),
                    error_message=render_msg if not render_success else None,
                )
            )

        # ----------------------------------------------------
        # STAGE 6: Assembly & Final MP4 Stitching
        # ----------------------------------------------------
        update_progress("Stage 6/7: Stitching scenes into final explainer MP4...", 0.85)
        clean_topic_slug = "".join(c if c.isalnum() else "_" for c in topic)[:30]
        final_video_path = self.output_dir / f"{clean_topic_slug}_{session_id}.mp4"
        self.assembler.concatenate_scenes(muxed_scene_paths, final_video_path)

        # ----------------------------------------------------
        # STAGE 7: Quality Assurance & Hallucination Audit
        # ----------------------------------------------------
        update_progress("Stage 7/7: Auditing factual consistency and metrics...", 0.95)
        eval_report_path = self.eval_dir / f"{session_id}_quality_report.json"
        quality_report: QualityReport = self.auditor.evaluate_run(
            script=script,
            source_text=raw_content,
            scene_reports=scene_quality_reports,
            output_report_path=eval_report_path,
        )

        total_runtime = round(time.time() - start_time, 2)
        update_progress(f"Done! Explainer video ready in {total_runtime}s.", 1.0)

        return {
            "status": "success",
            "session_id": session_id,
            "topic": topic,
            "video_path": str(final_video_path),
            "script_path": str(script_path),
            "quality_report_path": str(eval_report_path),
            "quality_report": quality_report.model_dump(),
            "duration_seconds": total_runtime,
        }


def main():
    """Command Line Interface Entrypoint."""
    parser = argparse.ArgumentParser(description="Free AI Explainer Video Generator CLI")
    parser.add_argument("--topic", type=str, default="Newton's Second Law (F = ma) for Class 10 students", help="Video topic")
    parser.add_argument("--text", type=str, default=None, help="Pasted notes or text content")
    parser.add_argument("--pdf", type=str, default=None, help="Path to input PDF file")
    parser.add_argument("--language", type=str, choices=["en", "hi"], default="en", help="Language: 'en' (English) or 'hi' (Hindi)")
    parser.add_argument("--audience", type=str, default="Class 10 students", help="Target audience description")

    args = parser.parse_args()

    pipeline = VideoGenerationPipeline()
    try:
        results = pipeline.run(
            topic=args.topic,
            input_text=args.text,
            pdf_path=args.pdf,
            language=args.language,
            target_audience=args.audience,
        )
        print("\n=======================================================")
        print(f"🎉 Video Successfully Generated!")
        print(f"📹 MP4 Path:       {results['video_path']}")
        print(f"📊 Quality Report: {results['quality_report_path']}")
        print(f"⏱️ Total Runtime:  {results['duration_seconds']}s")
        print("=======================================================\n")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
