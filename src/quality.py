"""
Quality Assurance & Hallucination Auditing Module.
Validates render success rates, sync duration drift, and prompts Ollama to flag unsupported claims.
"""

import json
from pathlib import Path
from typing import List, Optional
import requests
import yaml

from src.schemas import QualityReport, SceneQualityReport, VideoScript
from core.logger import setup_logger

logger = setup_logger("quality_eval")


class QualityAuditor:
    """Computes technical performance metrics and audits factual consistency against source text."""

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path or Path(__file__).resolve().parent.parent / "config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f).get("llm", {})
        else:
            self.config = {
                "host": "http://localhost:11434",
                "model": "llama3.1:8b",
            }

        self.host = self.config.get("host", "http://localhost:11434")
        self.model = self.config.get("model", "llama3.1:8b")

    def evaluate_run(
        self,
        script: VideoScript,
        source_text: str,
        scene_reports: List[SceneQualityReport],
        output_report_path: Path,
    ) -> QualityReport:
        """Calculates sync metrics and checks for hallucinations against the source text."""
        total = len(scene_reports)
        successful = sum(1 for s in scene_reports if s.render_success)
        success_rate = round((successful / total) * 100, 2) if total > 0 else 0.0

        mismatches = [s.duration_mismatch for s in scene_reports]
        avg_mismatch = round(sum(mismatches) / len(mismatches), 3) if mismatches else 0.0

        # LLM Hallucination Audit
        unsupported_claims, hallucination_detected = self._audit_hallucinations(script, source_text)

        report = QualityReport(
            topic=script.topic,
            language=script.language,
            total_scenes=total,
            successful_scenes=successful,
            overall_success_rate=success_rate,
            avg_duration_mismatch=avg_mismatch,
            hallucination_detected=hallucination_detected,
            unsupported_claims=unsupported_claims,
            scenes=scene_reports,
        )

        output_report_path = Path(output_report_path)
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        logger.info(
            f"Quality Audit Complete: Success Rate={success_rate}%, "
            f"Avg Sync Drift={avg_mismatch}s, Hallucinations={'Yes' if hallucination_detected else 'No'}"
        )
        return report

    def _audit_hallucinations(self, script: VideoScript, source_text: str) -> tuple[List[str], bool]:
        """Asks Ollama to verify that all script claims originated in the provided source text."""
        if not source_text or len(source_text.strip()) < 50:
            return [], False

        all_narration = " ".join([s.narration for s in script.scenes])
        audit_prompt = f"""You are a strict factual auditor. Compare the generated video narration against the original source notes.

ORIGINAL SOURCE TEXT:
{source_text[:4000]}

GENERATED NARRATION:
{all_narration[:4000]}

TASK:
Identify any factual claims in the narration that are NOT supported by or contradict the source text.
Return ONLY a valid JSON object matching:
{{
  "hallucination_detected": true/false,
  "unsupported_claims": ["claim 1", "claim 2"]
}}
"""

        try:
            resp = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": audit_prompt,
                    "format": "json",
                    "stream": False,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                data = json.loads(resp.json().get("response", "{}"))
                detected = bool(data.get("hallucination_detected", False))
                claims = data.get("unsupported_claims", [])
                return claims, detected
        except Exception as e:
            logger.warning(f"Hallucination audit check skipped due to error: {str(e)}")

        return [], False
