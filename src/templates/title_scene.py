"""
Title & Introduction Scene Template.
Features headline, subtitle, accent pill badge, and subtle dynamic glow.
"""

from manim import (
    Text, RoundedRectangle, VGroup, Line, UP, DOWN,
    Write, FadeIn, GrowFromCenter
)
from src.templates.base import (
    BaseExplainerScene, COLOR_TEXT, COLOR_ACCENT, COLOR_MUTED, COLOR_HIGHLIGHT
)


class TitleScene(BaseExplainerScene):
    """Renders a sleek, cinematic title card synchronized with introductory narration."""

    def build_scene(self):
        title_text = self.visual_data.get("title", "Topic Explainer")
        subtitle_text = self.visual_data.get("subtitle", "")
        accent_tag = self.visual_data.get("accent_text", "AI Explainer").upper()

        # 1. Accent Category Badge
        tag = Text(accent_tag, font_size=20, color=COLOR_HIGHLIGHT, weight="BOLD")
        badge = RoundedRectangle(
            corner_radius=0.15,
            height=tag.height + 0.25,
            width=tag.width + 0.6,
            color=COLOR_HIGHLIGHT,
            fill_color=COLOR_HIGHLIGHT,
            fill_opacity=0.15,
            stroke_width=2,
        )
        badge_group = VGroup(badge, tag).to_edge(UP, buff=1.2)

        # 2. Main Title
        main_title = Text(title_text, font_size=48, color=COLOR_TEXT, weight="BOLD")
        main_title.next_to(badge_group, DOWN, buff=0.5)

        # Subtle decorative divider line
        divider = Line(
            start=[-3, 0, 0],
            end=[3, 0, 0],
            color=COLOR_ACCENT,
            stroke_width=3
        ).next_to(main_title, DOWN, buff=0.4)

        # 3. Subtitle
        sub_group = VGroup()
        if subtitle_text:
            sub = Text(subtitle_text, font_size=28, color=COLOR_MUTED)
            sub.next_to(divider, DOWN, buff=0.4)
            sub_group.add(sub)

        # Timings
        timings = self.get_scaled_timings(total_phases=3)
        rt = timings["run_time"]

        # Animation Sequence
        self.play(FadeIn(badge_group, shift=DOWN * 0.3), run_time=rt * 0.8)
        self.play(Write(main_title), GrowFromCenter(divider), run_time=rt * 1.2)
        if sub_group:
            self.play(FadeIn(sub_group, shift=UP * 0.2), run_time=rt)

        self.wait(timings["hold_time"])
