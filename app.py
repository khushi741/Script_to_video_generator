"""
Streamlit Web UI for the Free AI Explainer Video Generator.
Supports text pasting, PDF uploads, language selection, progress tracking,
video playback, MP4 download, and quality assurance inspection.
"""

import os
import sys
from pathlib import Path
import streamlit as st

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.pipeline import VideoGenerationPipeline

st.set_page_config(
    page_title="AI Explainer Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.1rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<div class="main-title">🎬 Free AI Explainer Video Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Turn your notes or study topics into narrated, animated explainer videos using local AI. 100% Free & Open Source.</div>', unsafe_allow_html=True)

    # Sidebar Settings
    with st.sidebar:
        st.header("⚙️ Configuration")
        language = st.selectbox(
            "Narration Language",
            options=["en", "hi"],
            format_func=lambda x: "English (US - Aria)" if x == "en" else "Hindi (IN - Swara)",
            index=0,
        )

        audience = st.text_input("Target Audience", value="Class 10 students")

        st.markdown("---")
        st.subheader("💡 Tech Stack Status")
        st.markdown("- **LLM:** Ollama (Llama 3.1 / Qwen 2.5)")
        st.markdown("- **Animation:** Manim Community Edition")
        st.markdown("- **TTS:** edge-tts + Piper")
        st.markdown("- **Subtitles:** faster-whisper")
        st.markdown("- **Assembly:** FFmpeg + MoviePy")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("📝 Input Source")
        topic = st.text_input(
            "Topic / Chapter Title",
            value="Newton's Second Law (F = ma) for Class 10 students",
            placeholder="e.g. Photosynthesis, Binary Search, Newton's Laws...",
        )

        input_mode = st.radio("Choose Input Method", ["Paste Notes / Text", "Upload PDF Document"], horizontal=True)

        input_text = None
        uploaded_pdf_path = None

        if input_mode == "Paste Notes / Text":
            default_notes = (
                "Newton's Second Law of Motion states that the rate of change of momentum of an object "
                "is directly proportional to the applied unbalanced force and takes place in the direction of the force. "
                "Mathematically: F = m * a. Where F is the net force measured in Newtons (N), m is the mass of the object in kilograms (kg), "
                "and a is the acceleration in meters per second squared (m/s^2). "
                "For a given mass, a larger force produces greater acceleration. Conversely, for a given force, a heavier mass experiences less acceleration."
            )
            input_text = st.text_area("Paste Content / Chapter Excerpt", value=default_notes, height=220)
        else:
            uploaded_file = st.file_uploader("Upload Notes or Textbook Chapter (.pdf)", type=["pdf"])
            if uploaded_file is not None:
                # Save to storage/raw_uploads
                save_dir = Path(__file__).resolve().parent / "storage" / "raw_uploads"
                save_dir.mkdir(parents=True, exist_ok=True)
                temp_pdf = save_dir / uploaded_file.name
                with open(temp_pdf, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                uploaded_pdf_path = str(temp_pdf)
                st.success(f"PDF uploaded: {uploaded_file.name}")

        generate_btn = st.button("🚀 Generate Explainer Video", type="primary", use_container_width=True)

    with col2:
        st.subheader("📽️ Video Preview & Quality Audit")

        if generate_btn:
            if not topic.strip():
                st.error("Please provide a topic title.")
                return

            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_ui(msg: str, pct: float):
                progress_bar.progress(pct)
                status_text.info(msg)

            pipeline = VideoGenerationPipeline()

            try:
                with st.spinner("Executing autonomous 7-stage video pipeline..."):
                    result = pipeline.run(
                        topic=topic,
                        input_text=input_text,
                        pdf_path=uploaded_pdf_path,
                        language=language,
                        target_audience=audience,
                        progress_callback=update_ui,
                    )

                st.session_state["last_result"] = result
                st.success("🎉 Video generation completed successfully!")

            except Exception as e:
                st.error(f"Generation error: {str(e)}")
                st.info("Tip: Make sure Ollama is running (`ollama serve`) and FFmpeg is on your system PATH.")
                return

        # Display Result if available
        if "last_result" in st.session_state:
            res = st.session_state["last_result"]
            video_path = res.get("video_path")

            if video_path and os.path.exists(video_path):
                # Embedded Video Player
                st.video(video_path)

                # Download Button
                with open(video_path, "rb") as f:
                    video_bytes = f.read()

                st.download_button(
                    label="💾 Download Final MP4 Video",
                    data=video_bytes,
                    file_name=Path(video_path).name,
                    mime="video/mp4",
                    use_container_width=True,
                )

                # Quality Audit Section
                q_report = res.get("quality_report", {})
                with st.expander("📊 Quality & Hallucination Audit Report", expanded=True):
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    with m_col1:
                        st.metric("Total Scenes", q_report.get("total_scenes", 0))
                    with m_col2:
                        st.metric("Success Rate", f"{q_report.get('overall_success_rate', 100)}%")
                    with m_col3:
                        st.metric("Avg Sync Drift", f"{q_report.get('avg_duration_mismatch', 0.0)}s")
                    with m_col4:
                        hallucinated = q_report.get("hallucination_detected", False)
                        st.metric("Hallucinations", "Detected ⚠️" if hallucinated else "None ✅")

                    if q_report.get("unsupported_claims"):
                        st.warning("Flagged Claims (Not in Source Notes):")
                        for claim in q_report["unsupported_claims"]:
                            st.write(f"- {claim}")

                    st.json(q_report)
            else:
                st.info("No generated video in session.")


if __name__ == "__main__":
    main()
