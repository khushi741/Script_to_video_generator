"""
Diagram & Flowchart Scene Template.
Illustrates physical models, block diagrams, or causal flow vectors.
"""

from manim import (
    Text, RoundedRectangle, Arrow, VGroup, UP, DOWN, LEFT, RIGHT,
    Create, Write, FadeIn, GrowArrow
)
from src.templates.base import (
    BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_MUTED, COLOR_HIGHLIGHT
)


class DiagramScene(BaseExplainerScene):
    """Draws connected block diagrams, force vectors, and conceptual workflows."""

    def build_scene(self):
        title_text = self.visual_data.get("title", "Conceptual Model")
        elements = self.visual_data.get("elements", ["Input", "Process", "Output"])[:4]

        # Header
        header = Text(title_text, font_size=38, color=COLOR_ACCENT, weight="BOLD").to_edge(UP, buff=0.9)

        # Build Flow Blocks & Arrows
        block_groups = []
        arrow_list = []

        for item in elements:
            label = Text(item, font_size=22, color=COLOR_TEXT)
            rect = RoundedRectangle(
                corner_radius=0.15,
                height=label.height + 0.6,
                width=max(2.8, label.width + 0.6),
                color=COLOR_ACCENT,
                stroke_width=2,
                fill_color="#1E293B",
                fill_opacity=0.8,
            )
            block = VGroup(rect, label)
            block_groups.append(block)

        # Arrange horizontally
        diagram_chain = VGroup(*block_groups).arrange(RIGHT, buff=0.8).shift(DOWN * 0.2)

        # Build connecting arrows
        for i in range(len(block_groups) - 1):
            arr = Arrow(
                start=block_groups[i].get_right(),
                end=block_groups[i + 1].get_left(),
                color=COLOR_HIGHLIGHT,
                buff=0.15,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.3,
            )
            arrow_list.append(arr)

        # Timings
        phases = 1 + len(block_groups) + (len(arrow_list) if arrow_list else 0)
        timings = self.get_scaled_timings(total_phases=phases)
        rt = timings["run_time"]

        # Animate
        self.play(Write(header), run_time=rt * 0.9)

        for i, block in enumerate(block_groups):
            self.play(FadeIn(block, shift=UP * 0.3), run_time=rt * 0.8)
            if i < len(arrow_list):
                self.play(GrowArrow(arrow_list[i]), run_time=rt * 0.6)

        self.wait(timings["hold_time"])
