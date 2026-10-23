import pytest
from pydantic import ValidationError
from src.schemas import (
    TitleVisualData,
    BulletsVisualData,
    EquationVisualData,
    GraphVisualData,
    DiagramVisualData,
    SceneScript,
    VideoScript,
    QualityReport,
    SceneQualityReport,
)


def test_title_visual_data():
    data = TitleVisualData(title="Newton's Law", subtitle="Physics 101", accent_text="Chapter 2")
    assert data.title == "Newton's Law"
    assert data.subtitle == "Physics 101"
    assert data.accent_text == "Chapter 2"


def test_bullets_visual_data_validation():
    # Valid bullets (2 to 5 items)
    data = BulletsVisualData(heading="Core Principles", bullets=["Inertia", "Acceleration", "Action-Reaction"])
    assert len(data.bullets) == 3

    # Invalid bullets (< 2 items)
    with pytest.raises(ValidationError):
        BulletsVisualData(heading="Bad", bullets=["Only one point"])


def test_equation_visual_data():
    data = EquationVisualData(
        equation=r"F = m \cdot a",
        variables={"F": "Force", "m": "Mass", "a": "Acceleration"},
        explanation="Force causes proportional acceleration",
    )
    assert "F" in data.variables
    assert data.equation == r"F = m \cdot a"


def test_graph_visual_data_defaults():
    data = GraphVisualData(x_label="Time (s)", y_label="Velocity (m/s)")
    assert data.x_min == 0.0
    assert data.x_max == 10.0
    assert data.function_expr == "x"


def test_scene_script_narration_cleaning():
    scene = SceneScript(
        scene_id=1,
        title="Intro",
        narration="**Welcome** to `Physics` today! It is going to be exciting.",
        visual_type="title",
        visual_data={"title": "Physics Intro"},
    )
    # Checks markdown stripping validator
    assert "*" not in scene.narration
    assert "`" not in scene.narration
    assert "Welcome to Physics today!" in scene.narration


def test_video_script_validation():
    scenes = [
        SceneScript(
            scene_id=i,
            title=f"Scene {i}",
            narration=f"This is the detailed narration for scene number {i} of this lesson.",
            visual_type="bullets",
            visual_data={"heading": "Points", "bullets": ["A", "B"]},
        )
        for i in range(1, 4)
    ]
    script = VideoScript(topic="Test Lesson", language="en", scenes=scenes)
    assert len(script.scenes) == 3
    assert script.topic == "Test Lesson"

    # Test JSON serialization and deserialization
    json_str = script.model_dump_json()
    reloaded = VideoScript.model_validate_json(json_str)
    assert len(reloaded.scenes) == 3


def test_quality_report_metrics():
    scene_reports = [
        SceneQualityReport(
            scene_id=1,
            visual_type="title",
            render_success=True,
            audio_duration=12.5,
            video_duration=12.5,
            duration_mismatch=0.0,
        ),
        SceneQualityReport(
            scene_id=2,
            visual_type="bullets",
            render_success=True,
            audio_duration=15.0,
            video_duration=15.0,
            duration_mismatch=0.0,
        ),
    ]
    report = QualityReport(
        topic="Physics",
        language="en",
        total_scenes=2,
        successful_scenes=2,
        overall_success_rate=100.0,
        avg_duration_mismatch=0.0,
        hallucination_detected=False,
        scenes=scene_reports,
    )
    assert report.overall_success_rate == 100.0
    assert not report.hallucination_detected
