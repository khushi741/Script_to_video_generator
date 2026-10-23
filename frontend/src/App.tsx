import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { InputSection } from './components/InputSection';
import { ProgressTracker } from './components/ProgressTracker';
import { VideoPlayer } from './components/VideoPlayer';
import { QualityReportModal } from './components/QualityReportModal';
import { GenerateRequest, JobStatus, JobResult, SystemHealth } from './types';
import { checkSystemHealth, startVideoGeneration, fetchJobStatus } from './api';
import { PlayCircle, ShieldCheck, Film, Sparkles, CheckCircle2 } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth>({
    status: 'checking',
    ffmpeg_installed: false,
    ollama_running: false,
  });

  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<JobResult | null>(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Check initial backend health
  useEffect(() => {
    checkSystemHealth().then(setHealth);
    const interval = setInterval(() => {
      checkSystemHealth().then(setHealth);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Poll job status during generation
  useEffect(() => {
    if (!isGenerating || !currentJobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await fetchJobStatus(currentJobId);
        setJobStatus(status);

        if (status.status === 'completed') {
          setIsGenerating(false);
          if (status.result) {
            setResult(status.result);
          }
          clearInterval(pollInterval);
        } else if (status.status === 'failed') {
          setIsGenerating(false);
          setErrorBanner(status.error || 'Video generation failed.');
          clearInterval(pollInterval);
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    }, 1800);

    return () => clearInterval(pollInterval);
  }, [isGenerating, currentJobId]);

  const handleStartGeneration = async (req: GenerateRequest) => {
    setErrorBanner(null);
    setResult(null);
    try {
      setIsGenerating(true);
      const jobId = await startVideoGeneration(req);
      setCurrentJobId(jobId);
      setJobStatus({
        job_id: jobId,
        topic: req.topic,
        status: 'running',
        progress: 0.05,
        message: 'Initializing local AI pipeline...',
      });
    } catch (err: any) {
      setIsGenerating(false);
      setErrorBanner(err.message || 'Failed to start pipeline');
    }
  };

  return (
    <div className="app-container">
      <Header health={health} />

      {errorBanner && (
        <div style={{
          backgroundColor: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid var(--accent-rose)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem 1.25rem',
          marginBottom: '2rem',
          color: '#FECDD3',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <strong>Error: </strong> {errorBanner}
            <div style={{ fontSize: '0.82rem', marginTop: '0.2rem', color: '#FDA4AF' }}>
              Ensure Ollama is running (`ollama serve`) and FFmpeg is in your system PATH.
            </div>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            style={{ background: 'transparent', border: 'none', color: '#FECDD3', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}

      <main className="studio-grid">
        {/* Left Column: Input Form */}
        <section>
          <InputSection
            onGenerate={handleStartGeneration}
            isGenerating={isGenerating}
          />
        </section>

        {/* Right Column: Progress / Video Player / Preview */}
        <section>
          {isGenerating && jobStatus && (
            <ProgressTracker status={jobStatus} />
          )}

          {result && (
            <VideoPlayer
              result={result}
              onOpenReport={() => setShowReportModal(true)}
            />
          )}

          {!isGenerating && !result && (
            <div className="studio-card" style={{ textAlign: 'center', padding: '3.5rem 2rem' }}>
              <div style={{
                width: '64px',
                height: '64px',
                margin: '0 auto 1.5rem',
                borderRadius: '50%',
                background: 'rgba(56, 189, 248, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-cyan)',
              }}>
                <PlayCircle size={36} />
              </div>

              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                Video Preview & Playback Studio
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', maxWidth: '420px', margin: '0 auto 1.5rem' }}>
                Enter your topic or upload a chapter PDF on the left. The local AI will script, voice, animate, and stitch your video automatically.
              </p>

              <div style={{
                display: 'inline-flex',
                flexDirection: 'column',
                gap: '0.5rem',
                textAlign: 'left',
                background: 'var(--bg-card-subtle)',
                padding: '1rem 1.25rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.82rem',
                color: 'var(--text-secondary)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
                  <CheckCircle2 size={15} className="text-emerald-400" /> 100% Free & Open Source (No API Keys)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
                  <CheckCircle2 size={15} className="text-emerald-400" /> Runs on standard laptops (8–16 GB RAM)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
                  <CheckCircle2 size={15} className="text-emerald-400" /> Burned-in subtitles & multi-scene Manim animations
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Quality Report Modal */}
      {showReportModal && result && (
        <QualityReportModal
          report={result.quality_report}
          onClose={() => setShowReportModal(false)}
        />
      )}
    </div>
  );
};

export default App;
