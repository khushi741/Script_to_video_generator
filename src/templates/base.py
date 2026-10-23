"""
Base Manim Scene Template.
Provides duration-based timing synchronization, theme styling, and safe LaTeX/Unicode fallbacks.
"""

from typing import Dict, Any, Optional
from manim import Scene, Text, MathTex, VGroup, config as manim_config
from core.logger import setup_logger

logger = setup_logger("manim_base")

# Modern educational palette
COLOR_BG = "#0F172A"       # Dark Slate 900
COLOR_TEXT = "#F8FAFC"     # Slate 50
COLOR_ACCENT = "#38BDF8"   # Electric Sky Blue 400
COLOR_MUTED = "#94A3B8"    # Slate 400
COLOR_HIGHLIGHT = "#F59E0B"# Amber 500


class BaseExplainerScene(Scene):
    """
    Base class for all automated visual explainer scenes.
    Accepts target_duration and visual_data to dynamically synchronize animation lengths.
    """

    def __init__(self, visual_data: Optional[Dict[str, Any]] = None, target_duration: float = 10.0, **kwargs):
        self.visual_data = visual_data or {}
        self.target_duration = max(3.0, float(target_duration))
        super().__init__(**kwargs)

    def construct(self):
        # Set dark theme background
        self.camera.background_color = COLOR_BG
        self.build_scene()

    def build_scene(self):
        """Subclasses override this to construct specific visual elements."""
        raise NotImplementedError("Subclasses must implement build_scene()")

    def get_scaled_timings(self, total_phases: int) -> Dict[str, float]:
        """
        Dynamically divides target_duration among intro, animations, and hold time.
        Ensures animation finishes smoothly and holds until the narration ends.
        """
        if total_phases <= 0:
            total_phases = 1

        # Budget: 70% active animations, 30% hold / linger time
        active_time = self.target_duration * 0.70
        linger_time = self.target_duration * 0.30

        run_time_per_phase = max(0.6, active_time / total_phases)
        actual_active = run_time_per_phase * total_phases
        actual_hold = max(1.0, self.target_duration - actual_active)

        return {
            "run_time": run_time_per_phase,
            "hold_time": actual_hold,
            "total_target": self.target_duration,
        }

    def safe_math(self, formula: str, font_size: int = 44, color: str = COLOR_ACCENT) -> VGroup:
        """
        Creates a math object. Attempts MathTex first; if LaTeX is not installed
        or fails, falls back gracefully to a high-legibility Unicode Text object.
        """
        clean_formula = formula.strip()
        try:
            # Try official MathTex
            m = MathTex(clean_formula, font_size=font_size, color=color)
            return m
        except Exception as e:
            logger.info(f"LaTeX MathTex unavailable ({str(e)}). Using Unicode Text fallback.")
            # Convert basic LaTeX symbols to clean Unicode
            unicode_str = (
                clean_formula.replace("\\cdot", "·")
                .replace("\\times", "×")
                .replace("\\Delta", "Δ")
                .replace("\\approx", "≈")
                .replace("\\rightarrow", "→")
                .replace("\\frac{", "(")
                .replace("}{", "/")
                .replace("}", ")")
                .replace("{", "")
                .replace("}", "")
                .replace("\\", "")
            )
            t = Text(unicode_str, font_size=font_size - 4, color=color, weight="BOLD")
            return t
