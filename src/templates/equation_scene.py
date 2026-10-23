"""
Equation & Formula Scene Template.
Highlights a mathematical or physical equation, variables glossary, and descriptive takeaway.
"""

from manim import (
    Text, RoundedRectangle, VGroup, UP, DOWN, LEFT, RIGHT,
    Write, FadeIn, Create
)
from src.templates.base import (
    BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_MUTED, COLOR_HIGHLIGHT
)


class EquationScene(BaseExplainerScene):
    """Renders prominent formula cards with interactive breakdown of variables."""

    def build_scene(self):
        formula_str = self.visual_data.get("equation", "F = m \\cdot a")
        variables_map = self.visual_data.get("variables", {})
        explanation_text = self.visual_data.get("explanation", "")

        # 1. Formula Display via safe_math
        math_obj = self.safe_math(formula_str, font_size=52, color=COLOR_HIGHLIGHT)
        
        # Enclose in a glowing card
        card_box = RoundedRectangle(
            corner_radius=0.2,
            height=math_obj.height + 0.9,
            width=max(6.0, math_obj.width + 1.6),
            color=COLOR_ACCENT,
            stroke_width=2.5,
            fill_color="#1E293B",
            fill_opacity=0.7,
        )
        formula_card = VGroup(card_box, math_obj)
        formula_card.to_edge(UP, buff=1.0)

        # 2. Variable Breakdown List
        var_rows = []
        if variables_map:
            for symbol, meaning in list(variables_map.items())[:4]:
                sym_label = self.safe_math(symbol, font_size=32, color=COLOR_ACCENT)
                eq_sign = Text(":", font_size=26, color=COLOR_MUTED)
                desc = Text(str(meaning), font_size=24, color=COLOR_TEXT)
                
                row = VGroup(sym_label, eq_sign, desc).arrange(RIGHT, buff=0.2)
                var_rows.append(row)

        vars_group = VGroup(*var_rows)
        if var_rows:
            vars_group.arrange(DOWN, aligned_edge=LEFT, buff=0.35)
            vars_group.next_to(formula_card, DOWN, buff=0.6)

        # 3. Bottom Takeaway / Explanation
        expl_group = VGroup()
        if explanation_text:
            expl = Text(explanation_text, font_size=22, color=COLOR_MUTED)
            expl.to_edge(DOWN, buff=0.8)
            expl_group.add(expl)

        # Timings
        phases = 2 + (1 if var_rows else 0) + (1 if explanation_text else 0)
        timings = self.get_scaled_timings(total_phases=phases)
        rt = timings["run_time"]

        # Animations
        self.play(Create(card_box), Write(math_obj), run_time=rt * 1.2)
        if var_rows:
            self.play(FadeIn(vars_group, shift=UP * 0.3), run_time=rt)
        if expl_group:
            self.play(FadeIn(expl_group, shift=UP * 0.2), run_time=rt * 0.8)

        self.wait(timings["hold_time"])
