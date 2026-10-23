"""
Graph & Coordinate Plot Scene Template.
Renders clean 2D mathematical relationships, labeled axes, and plotted curves.
"""

import math
from manim import (
    Axes, Text, VGroup, UP, DOWN, LEFT,
    Create, Write, FadeIn
)
from src.templates.base import (
    BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_MUTED, COLOR_HIGHLIGHT
)


class GraphScene(BaseExplainerScene):
    """Plots mathematical functions and real-world trends on animated coordinate axes."""

    def build_scene(self):
        title_text = self.visual_data.get("title", "Relationship Analysis")
        x_label = self.visual_data.get("x_label", "x")
        y_label = self.visual_data.get("y_label", "y")
        func_expr = self.visual_data.get("function_expr", "x")
        x_min = float(self.visual_data.get("x_min", 0.0))
        x_max = float(self.visual_data.get("x_max", 10.0))

        # Title
        header = Text(title_text, font_size=36, color=COLOR_ACCENT, weight="BOLD").to_edge(UP, buff=0.8)

        # Build Axes
        axes = Axes(
            x_range=[x_min, x_max, max(1.0, (x_max - x_min) / 5)],
            y_range=[0, 10, 2],
            x_length=7.5,
            y_length=4.2,
            axis_config={"color": COLOR_MUTED, "stroke_width": 2},
            tips=True,
        ).shift(DOWN * 0.4 + LEFT * 0.5)

        x_lbl = Text(x_label, font_size=20, color=COLOR_TEXT).next_to(axes.x_axis, DOWN, buff=0.3)
        y_lbl = Text(y_label, font_size=20, color=COLOR_TEXT).next_to(axes.y_axis, UP, buff=0.3)
        labels = VGroup(x_lbl, y_lbl)

        # Safe Function Evaluator
        def safe_eval_func(x_val: float) -> float:
            allowed_names = {
                "x": x_val,
                "sin": math.sin,
                "cos": math.cos,
                "sqrt": math.sqrt,
                "exp": math.exp,
                "log": math.log,
            }
            try:
                val = eval(func_expr, {"__builtins__": {}}, allowed_names)
                return max(0.0, min(10.0, float(val)))
            except Exception:
                return x_val

        curve = axes.plot(safe_eval_func, x_range=[x_min, x_max], color=COLOR_HIGHLIGHT, stroke_width=4)

        # Timings
        timings = self.get_scaled_timings(total_phases=3)
        rt = timings["run_time"]

        # Animation Sequence
        self.play(Write(header), Create(axes), FadeIn(labels), run_time=rt * 1.1)
        self.play(Create(curve), run_time=rt * 1.2)
        self.wait(timings["hold_time"])
