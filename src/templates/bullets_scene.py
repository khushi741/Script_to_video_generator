"""
Bullet Points & Concepts Scene Template.
Sequentially animates numbered or highlighted list points.
"""

from manim import (
    Text, Dot, VGroup, UP, DOWN, LEFT, RIGHT,
    FadeIn, Write
)
from src.templates.base import (
    BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_MUTED, COLOR_HIGHLIGHT
)


class BulletsScene(BaseExplainerScene):
    """Renders structured key points or takeaways in clear sequential animations."""

    def build_scene(self):
        heading_text = self.visual_data.get("heading", "Key Concepts")
        bullets = self.visual_data.get("bullets", ["Point 1", "Point 2", "Point 3"])

        # 1. Header
        header = Text(heading_text, font_size=40, color=COLOR_ACCENT, weight="BOLD")
        header.to_edge(UP, buff=1.0)

        # 2. Bullet list
        bullet_groups = []
        for i, text in enumerate(bullets[:5]):  # Cap at 5 points for visual cleanliness
            dot = Dot(radius=0.1, color=COLOR_HIGHLIGHT)
            b_text = Text(text, font_size=26, color=COLOR_TEXT)
            b_text.next_to(dot, RIGHT, buff=0.3)
            row = VGroup(dot, b_text)
            bullet_groups.append(row)

        all_bullets = VGroup(*bullet_groups)
        all_bullets.arrange(DOWN, aligned_edge=LEFT, buff=0.55)
        all_bullets.next_to(header, DOWN, buff=0.8)

        # Timings
        phases = 1 + len(bullet_groups)
        timings = self.get_scaled_timings(total_phases=phases)
        rt = timings["run_time"]

        # Animate Header
        self.play(Write(header), run_time=rt)

        # Animate each bullet sequentially
        for row in bullet_groups:
            self.play(FadeIn(row, shift=RIGHT * 0.4), run_time=rt * 0.9)

        self.wait(timings["hold_time"])
