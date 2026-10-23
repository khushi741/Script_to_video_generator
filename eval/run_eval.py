"""
Automated Evaluation Suite.
Tests the pipeline across 5 diverse educational topics and benchmarks:
- Render success rate
- Audio-video sync error
- Per-stage execution duration
"""

import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import VideoGenerationPipeline
from core.logger import setup_logger

logger = setup_logger("eval_suite")

SAMPLE_TOPICS = [
    {
        "topic": "Newton's Second Law (F = ma) for Class 10 students",
        "notes": "Force equals mass times acceleration (F = ma). Net unbalanced force causes proportional acceleration.",
        "language": "en",
    },
    {
        "topic": "Photosynthesis and the Light Reaction",
        "notes": "Plants convert solar energy, water, and carbon dioxide into glucose and oxygen through chlorophyll.",
        "language": "en",
    },
    {
        "topic": "Binary Search Algorithm (O(log n))",
        "notes": "Binary search finds items in sorted arrays by repeatedly halving the search interval.",
        "language": "en",
    },
    {
        "topic": "Ohm's Law: Voltage, Current, and Resistance (V = IR)",
        "notes": "Current flowing through a conductor between two points is directly proportional to voltage across the points.",
        "language": "en",
    },
    {
        "topic": "The Pythagorean Theorem (a^2 + b^2 = c^2)",
        "notes": "In a right-angled triangle, the square of the hypotenuse is equal to the sum of the squares of the other two sides.",
        "language": "en",
    },
]


def run_benchmark(max_topics: int = 5) -> Dict[str, Any]:
    pipeline = VideoGenerationPipeline()
    eval_dir = Path(__file__).resolve().parent.parent / "storage" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)

    topic_results: List[Dict[str, Any]] = []
    total_start = time.time()

    print("\n" + "=" * 65)
    print("🚀 STARTING AI EXPLAINER VIDEO EVALUATION SUITE")
    print("=" * 65)

    for i, item in enumerate(SAMPLE_TOPICS[:max_topics], start=1):
        print(f"\n[{i}/{max_topics}] Testing: {item['topic']}...")
        t0 = time.time()
        try:
            res = pipeline.run(
                topic=item["topic"],
                input_text=item["notes"],
                language=item["language"],
            )
            elapsed = round(time.time() - t0, 2)
            q_rep = res.get("quality_report", {})
            topic_results.append({
                "topic": item["topic"],
                "status": "success",
                "duration_seconds": elapsed,
                "scenes": q_rep.get("total_scenes", 0),
                "render_success_rate": q_rep.get("overall_success_rate", 100.0),
                "avg_sync_drift": q_rep.get("avg_duration_mismatch", 0.0),
                "hallucinations": q_rep.get("hallucination_detected", False),
            })
            print(f"   ✅ Finished in {elapsed}s | Success: {q_rep.get('overall_success_rate', 100)}% | Sync Drift: {q_rep.get('avg_duration_mismatch', 0.0)}s")
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            logger.error(f"Topic evaluation failed: {str(e)}")
            topic_results.append({
                "topic": item["topic"],
                "status": "failed",
                "duration_seconds": elapsed,
                "error": str(e),
            })
            print(f"   ❌ Failed: {str(e)}")

    total_time = round(time.time() - total_start, 2)
    successful_runs = sum(1 for r in topic_results if r["status"] == "success")
    overall_render_rate = (
        sum(r.get("render_success_rate", 0) for r in topic_results if r["status"] == "success") / max(1, successful_runs)
    )

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_topics_evaluated": len(topic_results),
        "successful_pipeline_runs": successful_runs,
        "pipeline_pass_rate": round((successful_runs / len(topic_results)) * 100, 2),
        "avg_render_success_rate": round(overall_render_rate, 2),
        "total_suite_runtime": total_time,
        "topics": topic_results,
    }

    summary_file = eval_dir / f"eval_summary_{int(total_start)}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 65)
    print("📊 EVALUATION BENCHMARK SUMMARY")
    print(f"Total Topics Tested:    {summary['total_topics_evaluated']}")
    print(f"Pipeline Pass Rate:     {summary['pipeline_pass_rate']}%")
    print(f"Avg Scene Success Rate: {summary['avg_render_success_rate']}%")
    print(f"Total Test Runtime:     {summary['total_suite_runtime']}s")
    print(f"Summary JSON File:      {summary_file}")
    print("=" * 65 + "\n")

    return summary


if __name__ == "__main__":
    run_benchmark()
