"""
Strict Pydantic schemas for script generation, scene visual data, and quality checks.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class TitleVisualData(BaseModel):
    title: str = Field(..., description="Main headline or title")
    subtitle: Optional[str] = Field(None, description="Subtitle or secondary context")
    accent_text: Optional[str] = Field(None, description="Short kicker or topic tag")


class BulletsVisualData(BaseModel):
    heading: str = Field(..., description="Title for the list")
    bullets: List[str] = Field(..., min_length=2, max_length=5, description="2 to 5 clear, concise bullet points")


class EquationVisualData(BaseModel):
    equation: str = Field(..., description=r"Math or physics formula e.g. 'F = m \cdot a'")
    variables: Dict[str, str] = Field(default_factory=dict, description="Map of variable symbols to explanations")
    explanation: Optional[str] = Field(None, description="Short concept summary under the formula")


class GraphVisualData(BaseModel):
    title: Optional[str] = Field("Relationship Plot", description="Graph heading")
    x_label: str = Field("x", description="Label for horizontal axis")
    y_label: str = Field("y", description="Label for vertical axis")
    function_expr: str = Field("x", description="Python-evaluable expression of x, e.g., 'x', '2*x', 'x**2'")
    x_min: float = Field(0.0, description="Minimum x-axis value")
    x_max: float = Field(10.0, description="Maximum x-axis value")
    highlight_points: Optional[List[Dict[str, float]]] = Field(default_factory=list, description="Optional points to highlight [{'x': 2, 'y': 4}]")


class DiagramVisualData(BaseModel):
    title: Optional[str] = Field("Conceptual Diagram", description="Diagram title")
    diagram_type: Literal["vector_box", "flow", "cycle"] = Field("vector_box", description="Style of diagram")
    elements: List[str] = Field(..., min_length=2, max_length=5, description="Labels or components in the diagram")
    connections: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Pairs of connected elements [{'from': 'A', 'to': 'B'}]")


class SceneScript(BaseModel):
    scene_id: int = Field(..., ge=1, description="Sequential 1-based scene index")
    title: str = Field(..., min_length=2, description="Short title describing this scene")
    narration: str = Field(..., min_length=10, description="Full spoken narration script for this scene")
    visual_type: Literal["title", "bullets", "equation", "graph", "diagram"] = Field(..., description="The visualization template to use")
    visual_data: Dict[str, Any] = Field(..., description="Structured parameters matching visual_type")
    freeform_code: Optional[str] = Field(None, description="Optional freeform Manim Python code if enabled")

    @field_validator("narration")
    @classmethod
    def clean_narration(cls, v: str) -> str:
        # Strip extraneous markdown or quotes from narration text
        return v.replace("*", "").replace("`", "").strip()


class VideoScript(BaseModel):
    topic: str = Field(..., description="The core topic or title of the video")
    target_audience: Optional[str] = Field("Students / General audience", description="Target audience")
    language: Literal["en", "hi"] = Field("en", description="Narration language ('en' for English, 'hi' for Hindi)")
    scenes: List[SceneScript] = Field(..., min_length=3, max_length=10, description="List of sequential scenes (4-8 recommended)")


class SceneQualityReport(BaseModel):
    scene_id: int
    visual_type: str
    render_success: bool
    audio_duration: float
    video_duration: float
    duration_mismatch: float
    retry_count: int = 0
    used_fallback: bool = False
    error_message: Optional[str] = None


class QualityReport(BaseModel):
    topic: str
    language: str
    total_scenes: int
    successful_scenes: int
    overall_success_rate: float
    avg_duration_mismatch: float
    hallucination_detected: bool = False
    unsupported_claims: List[str] = Field(default_factory=list)
    scenes: List[SceneQualityReport] = Field(default_factory=list)
