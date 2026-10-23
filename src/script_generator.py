"""
Script generator module interfacing with Ollama HTTP API.
Generates strict structured JSON scene scripts with Pydantic validation and error feedback retries.
"""

import os
import json
import re
from typing import Optional, Dict, Any
import requests
import yaml
from pathlib import Path

from src.schemas import VideoScript, SceneScript
from core.logger import setup_logger

logger = setup_logger("script_generator")


SYSTEM_PROMPT = """You are an expert educational video director and animator.
Your task is to convert study notes or educational topics into a structured, highly engaging 4 to 8 scene explainer video script.

STRICT JSON OUTPUT REQUIREMENT:
You must return ONLY a single, valid JSON object matching the schema below.
No Markdown formatting around the JSON, no backticks (```json), no conversational preamble, no trailing commentary.

REQUIRED JSON SCHEMA:
{
  "topic": "Topic Title",
  "target_audience": "Class 10 students or General learners",
  "language": "en",
  "scenes": [
    {
      "scene_id": 1,
      "title": "Catchy Scene Title",
      "narration": "Full spoken narration script for this scene. Spoken naturally, conversational, clear, and engaging.",
      "visual_type": "title",
      "visual_data": {
        "title": "Main Title",
        "subtitle": "Subtitle or topic focus",
        "accent_text": "Class 10 Physics"
      }
    },
    {
      "scene_id": 2,
      "title": "Key Concepts",
      "narration": "Narration introducing the 3 key pillars of this topic.",
      "visual_type": "bullets",
      "visual_data": {
        "heading": "Core Principles",
        "bullets": ["Point 1", "Point 2", "Point 3"]
      }
    },
    {
      "scene_id": 3,
      "title": "The Mathematical Formula",
      "narration": "Explaining the formula and what each variable represents.",
      "visual_type": "equation",
      "visual_data": {
        "equation": "F = m \\cdot a",
        "variables": {"F": "Net Force (Newtons)", "m": "Mass (kg)", "a": "Acceleration (m/s^2)"},
        "explanation": "Force is directly proportional to mass and acceleration."
      }
    },
    {
      "scene_id": 4,
      "title": "Visualizing the Relationship",
      "narration": "Looking at the graph, as force increases for a constant mass, acceleration increases proportionally.",
      "visual_type": "graph",
      "visual_data": {
        "title": "Force vs. Acceleration",
        "x_label": "Acceleration (a)",
        "y_label": "Force (F)",
        "function_expr": "2*x",
        "x_min": 0.0,
        "x_max": 10.0
      }
    },
    {
      "scene_id": 5,
      "title": "Real-World Demonstration",
      "narration": "Imagine pushing a lightweight bicycle versus a heavy truck. The heavier mass requires far more force.",
      "visual_type": "diagram",
      "visual_data": {
        "title": "Mass vs. Required Force",
        "diagram_type": "vector_box",
        "elements": ["Small Mass (Cart)", "Large Force Vector", "High Acceleration"]
      }
    }
  ]
}

VISUAL TYPE RULES:
1. "title": Used for introduction. visual_data requires 'title', optional 'subtitle', optional 'accent_text'.
2. "bullets": Used for core principles or lists. visual_data requires 'heading' and 'bullets' (list of 2-5 strings).
3. "equation": Used for laws, theorems, or formulas. visual_data requires 'equation' (LaTeX or standard notation), 'variables' (dict), and 'explanation'.
4. "graph": Used for relationships or curves. visual_data requires 'x_label', 'y_label', 'function_expr' (Python math like 'x', '2*x', '0.5*x**2'), 'x_min', 'x_max'.
5. "diagram": Used for systems, cycles, or forces. visual_data requires 'title', 'diagram_type' ('vector_box', 'flow', or 'cycle'), and 'elements' (list of 2-5 strings).

NARRATION RULES:
- Write continuous, spoken English (or Hindi if requested).
- Do not put bracketed cues in narration like [pause] or [smile].
- Ensure each scene's narration takes between 10 to 25 seconds to read comfortably (approx 30 to 70 words per scene).
- Maintain 4 to 8 total scenes.
"""


class ScriptGenerator:
    """Interacts with local Ollama instance to generate and validate video scripts."""

    def __init__(self, config_path: Optional[str] = None):
        cfg_file = Path(config_path or Path(__file__).resolve().parent.parent / "config.yaml")
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "llm": {
                    "host": "http://localhost:11434",
                    "model": "llama3.1:8b",
                    "timeout_seconds": 180,
                    "temperature": 0.2,
                    "max_retries": 3,
                }
            }

        self.host = self.config.get("llm", {}).get("host", "http://localhost:11434")
        self.model = self.config.get("llm", {}).get("model", "llama3.1:8b")
        self.timeout = self.config.get("llm", {}).get("timeout_seconds", 180)
        self.max_retries = self.config.get("llm", {}).get("max_retries", 3)

    def check_ollama_status(self) -> bool:
        """Verifies if the local Ollama daemon is active and accessible."""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            if resp.status_code == 200:
                logger.info(f"Ollama server is reachable at {self.host}")
                return True
        except requests.exceptions.RequestException:
            pass

        logger.error(
            f"Ollama is NOT running or unreachable at {self.host}.\n"
            "Action required: Install Ollama (https://ollama.com) and start it via 'ollama serve' in your terminal."
        )
        return False

    def generate_script(
        self,
        content: str,
        topic: str = "Educational Topic",
        target_audience: str = "Students",
        language: str = "en",
    ) -> VideoScript:
        """
        Generates a validated VideoScript from input content.
        Employs recursive retry loops feeding schema errors back to the LLM on failure.
        """
        if not self.check_ollama_status():
            allow_fallback = os.getenv("ALLOW_OFFLINE_FALLBACK", "true").lower() in ("true", "1", "yes")
            if allow_fallback:
                logger.warning(
                    f"Ollama is unreachable at {self.host}. Generating high-fidelity fallback script for topic: '{topic}'."
                )
                return self._build_deterministic_fallback(topic, content, language)
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.host}. Please ensure Ollama is installed and running (`ollama serve`)."
            )

        lang_instruction = "English" if language == "en" else "Hindi (using Devanagari script for narration)"
        user_prompt = (
            f"TOPIC: {topic}\n"
            f"TARGET AUDIENCE: {target_audience}\n"
            f"LANGUAGE FOR NARRATION: {lang_instruction}\n\n"
            f"SOURCE CONTENT TO ADAPT INTO 4-8 SCENES:\n"
            f"{content[:8000]}\n\n"
            "Generate the complete JSON script now adhering strictly to the schema."
        )

        feedback = ""
        last_raw_response = ""

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Generating script with Ollama ({self.model}) - Attempt {attempt}/{self.max_retries}")

            prompt = user_prompt
            if feedback:
                prompt += f"\n\nPREVIOUS ATTEMPT FAILED WITH VALIDATION ERROR:\n{feedback}\nPlease fix the JSON and return valid JSON."

            try:
                raw_json_str = self._call_ollama(prompt)
                last_raw_response = raw_json_str
                cleaned_json = self._extract_json_string(raw_json_str)

                # Parse JSON
                data = json.loads(cleaned_json)

                # Overwrite/ensure language matches requested
                data["language"] = language
                if "topic" not in data or not data["topic"]:
                    data["topic"] = topic

                # Validate with Pydantic
                video_script = VideoScript.model_validate(data)
                logger.info(f"Successfully generated and validated VideoScript with {len(video_script.scenes)} scenes.")
                return video_script

            except (json.JSONDecodeError, ValueError) as err:
                logger.warning(f"Attempt {attempt} validation failed: {str(err)}")
                feedback = f"Error parsing or validating JSON: {str(err)}\nEnsure valid JSON without unescaped quotes."

        # If all retries fail, construct a robust fallback script
        logger.error("All Ollama script generation attempts failed. Building deterministic fallback script.")
        return self._build_deterministic_fallback(topic, content, language)

    def _call_ollama(self, prompt: str) -> str:
        """Calls the Ollama HTTP API endpoint."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.config.get("llm", {}).get("temperature", 0.2),
            },
        }

        resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama API returned HTTP {resp.status_code}: {resp.text}")

        res_data = resp.json()
        return res_data.get("response", "{}")

    @staticmethod
    def _extract_json_string(raw_text: str) -> str:
        """Strips markdown code blocks, preambles, and extracts clean JSON."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\n?```$", "", text)

        # Find first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start : end + 1]
        return text

    def _build_deterministic_fallback(self, topic: str, content: str, language: str) -> VideoScript:
        """Guarantees a viable script if Ollama fails or produces corrupted JSON."""
        clean_snip = content[:250].replace("\n", " ").strip()
        scenes = [
            SceneScript(
                scene_id=1,
                title=f"Introduction to {topic}",
                narration=f"Welcome to this explainer on {topic}. Today we will explore the foundational principles and practical applications.",
                visual_type="title",
                visual_data={"title": topic, "subtitle": "Core Principles Explained", "accent_text": "Educational Guide"},
            ),
            SceneScript(
                scene_id=2,
                title="Overview & Key Concepts",
                narration=f"Let's break down the main ideas. {clean_snip}",
                visual_type="bullets",
                visual_data={"heading": "Key Principles", "bullets": ["Fundamental Definition", "Core Mechanism", "Practical Significance"]},
            ),
            SceneScript(
                scene_id=3,
                title="Mathematical Foundation",
                narration="Every physical principle is governed by quantitative relationships that let us predict outcomes.",
                visual_type="equation",
                visual_data={"equation": "F = m \\cdot a", "variables": {"F": "Force", "m": "Mass", "a": "Acceleration"}, "explanation": "Direct linear proportionality between variables."},
            ),
            SceneScript(
                scene_id=4,
                title="Summary & Conclusion",
                narration="In conclusion, understanding these relationships gives us the power to analyze real-world physical systems with precision.",
                visual_type="bullets",
                visual_data={"heading": "Takeaway Summary", "bullets": ["Observe the variables", "Apply the core formula", "Verify with real-world examples"]},
            ),
        ]
        return VideoScript(topic=topic, language=language, scenes=scenes)
