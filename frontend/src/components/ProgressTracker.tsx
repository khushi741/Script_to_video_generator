import React from 'react';
import { Check, Loader2 } from 'lucide-react';
import { JobStatus } from '../types';

interface ProgressTrackerProps {
  status: JobStatus;
}

const PIPELINE_STAGES = [
  { id: 1, label: "Ingest & Text Sanitization", minPct: 0.05 },
  { id: 2, label: "Script Generation (Ollama JSON)", minPct: 0.15 },
  { id: 3, label: "Narration Synthesis (edge-tts / Piper)", minPct: 0.30 },
  { id: 4, label: "Subtitle Timestamps (faster-whisper int8)", minPct: 0.50 },
  { id: 5, label: "Manim Visual Animation Rendering", minPct: 0.70 },
  { id: 6, label: "FFmpeg Mux & Scene Concatenation", minPct: 0.85 },
  { id: 7, label: "Quality Audit & Hallucination Check", minPct: 0.95 },
];

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ status }) => {
  const currentPct = Math.round(status.progress * 100);

  return (
    <div className="studio-card progress-card">
      <div className="progress-header">
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Loader2 className="animate-spin text-sky-400" size={16} />
          <span>{status.message}</span>
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
          {currentPct}%
        </span>
      </div>

      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${currentPct}%` }} />
      </div>

      <div className="timeline-stages">
        {PIPELINE_STAGES.map((stage) => {
          const isCompleted = status.progress >= stage.minPct + 0.10 || status.status === 'completed';
          const isActive = !isCompleted && status.progress >= stage.minPct;

          return (
            <div
              key={stage.id}
              className={`timeline-step ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
            >
              <div className="step-indicator">
                {isCompleted ? <Check size={12} /> : stage.id}
              </div>
              <span>{stage.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
