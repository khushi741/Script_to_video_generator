import React from 'react';
import { X, CheckCircle2, AlertTriangle, ShieldCheck, Clock } from 'lucide-react';
import { QualityReport } from '../types';

interface QualityReportModalProps {
  report: QualityReport;
  onClose: () => void;
}

export const QualityReportModal: React.FC<QualityReportModalProps> = ({ report, onClose }) => {
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: '2rem',
    }}>
      <div className="studio-card" style={{ maxWidth: '850px', width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h2 className="card-title" style={{ fontSize: '1.3rem' }}>
              <ShieldCheck className="text-emerald-400" size={22} />
              Quality & Hallucination Audit
            </h2>
            <p className="card-desc" style={{ marginBottom: 0 }}>Automated synchronization and factual consistency audit report</p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <X size={22} />
          </button>
        </div>

        {/* 4 Metric Boxes */}
        <div className="metrics-grid">
          <div className="metric-box">
            <div className="metric-val">{report.total_scenes}</div>
            <div className="metric-lbl">Total Scenes</div>
          </div>

          <div className="metric-box">
            <div className="metric-val" style={{ color: 'var(--accent-emerald)' }}>
              {report.overall_success_rate}%
            </div>
            <div className="metric-lbl">Render Success Rate</div>
          </div>

          <div className="metric-box">
            <div className="metric-val" style={{ color: 'var(--accent-cyan)' }}>
              {report.avg_duration_mismatch}s
            </div>
            <div className="metric-lbl">Avg Sync Drift</div>
          </div>

          <div className="metric-box">
            <div className="metric-val" style={{ color: report.hallucination_detected ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
              {report.hallucination_detected ? 'Alert' : 'Clean'}
            </div>
            <div className="metric-lbl">Factual Integrity</div>
          </div>
        </div>

        {/* Hallucination Alerts */}
        {report.hallucination_detected && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid var(--accent-rose)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
            marginBottom: '1.5rem',
          }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-rose)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              <AlertTriangle size={16} />
              Flagged Claims (Not Found in Source Notes)
            </h4>
            <ul style={{ paddingLeft: '1.2rem', fontSize: '0.84rem', color: 'var(--text-primary)' }}>
              {report.unsupported_claims.map((claim, idx) => (
                <li key={idx} style={{ marginBottom: '0.25rem' }}>{claim}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Scene-by-Scene Table */}
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.5rem' }}>
          Scene-by-Scene Alignment Breakdown
        </h4>
        <table className="scene-table">
          <thead>
            <tr>
              <th>Scene</th>
              <th>Visual Type</th>
              <th>Audio Duration</th>
              <th>Video Duration</th>
              <th>Sync Drift</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {report.scenes.map((scene) => (
              <tr key={scene.scene_id}>
                <td style={{ fontWeight: 600 }}>#{scene.scene_id}</td>
                <td>
                  <span className={`badge-tag ${scene.visual_type}`}>
                    {scene.visual_type}
                  </span>
                </td>
                <td>{scene.audio_duration}s</td>
                <td>{scene.video_duration}s</td>
                <td style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                  {scene.duration_mismatch}s
                </td>
                <td>
                  {scene.render_success ? (
                    <span style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <CheckCircle2 size={14} /> Rendered
                    </span>
                  ) : (
                    <span style={{ color: 'var(--accent-rose)' }}>Failed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
