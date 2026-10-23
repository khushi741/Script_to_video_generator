import React from 'react';
import { Download, Film, BarChart3 } from 'lucide-react';
import { JobResult } from '../types';
import { getVideoDownloadUrl } from '../api';

interface VideoPlayerProps {
  result: JobResult;
  onOpenReport: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ result, onOpenReport }) => {
  const videoUrl = getVideoDownloadUrl((result as any).job_id || result.session_id);

  return (
    <div className="studio-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
        <h3 className="card-title" style={{ fontSize: '1.15rem' }}>
          <Film className="text-sky-400" size={18} />
          {result.topic}
        </h3>
        <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(56, 189, 248, 0.15)', color: 'var(--accent-cyan)', fontWeight: 700 }}>
          1080p MP4
        </span>
      </div>

      <div className="video-wrapper">
        <video
          className="video-element"
          controls
          autoPlay
          src={videoUrl}
        >
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="video-actions">
        <a
          href={videoUrl}
          download={`${result.topic.slice(0, 30)}.mp4`}
          className="btn-download"
        >
          <Download size={16} />
          Download Explainer MP4
        </a>

        <button
          type="button"
          className="btn-download"
          onClick={onOpenReport}
          style={{ cursor: 'pointer' }}
        >
          <BarChart3 size={16} className="text-amber-400" />
          View Quality & Audit Report
        </button>
      </div>
    </div>
  );
};
