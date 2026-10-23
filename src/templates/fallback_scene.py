"""
Robust Fallback Scene Template.
Guaranteed to render without dependencies if a primary template fails.
"""

from manim import Text, RoundedRectangle, VGroup, UP, DOWN, Write, FadeIn
from src.templates.base import BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_HIGHLIGHT


class FallbackScene(BaseExplainerScene):
    """Safe fallback scene to ensure zero video generation crashes."""

    def build_scene(self):
        title = self.visual_data.get("title", "Key Takeaway")
        summary = self.visual_data.get("summary", "Understanding core concepts through systematic analysis.")

        header = Text(title, font_size=42, color=COLOR_HIGHLIGHT, weight="BOLD").to_edge(UP, buff=1.2)

        # Content Card
        box = RoundedRectangle(
            corner_radius=0.2,
            height=3.5,
            width=9.5,
            color=COLOR_ACCENT,
            stroke_width=2,
            fill_color="#1E293B",
            fill_opacity=0.6,
        )

        words = summary.split()
        lines = []
        for i in range(0, len(words), 8):
            lines.append(" ".join(words[i : i + 8]))
        body_text = "\n".join(lines[:4])

        content = Text(body_text, font_size=26, color=COLOR_TEXT, line_spacing=0.8).move_to(box)
        card = VGroup(box, content).next_to(header, DOWN, buff=0.6)

        timings = self.get_scaled_timings(total_phases=2)
        rt = timings["run_time"]

        self.play(Write(header), run_time=rt)
        self.play(FadeIn(card, shift=UP * 0.3), run_time=rt)
        self.wait(timings["hold_time"])
