import React from 'react';
import { Film, CheckCircle2, AlertCircle, Cpu } from 'lucide-react';
import { SystemHealth } from '../types';

interface HeaderProps {
  health: SystemHealth;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  return (
    <header className="app-header">
      <div className="logo-group">
        <div className="logo-badge">
          <Film className="w-6 h-6 text-sky-400" />
        </div>
        <div>
          <h1 className="logo-title">AI Explainer Video Studio</h1>
          <p className="logo-subtitle">Local, autonomous animated explainer video generation with Manim & Ollama</p>
        </div>
      </div>

      <div className="health-status-bar">
        <div className="status-indicator">
          <Cpu size={14} className="text-slate-400" />
          <span>Ollama LLM:</span>
          <span className={`status-dot ${health.ollama_running ? 'online' : 'offline'}`} />
          <span style={{ color: health.ollama_running ? '#10B981' : '#F43F5E', fontWeight: 600 }}>
            {health.ollama_running ? 'Active (llama3.1)' : 'Offline'}
          </span>
        </div>

        <div className="status-indicator">
          <Film size={14} className="text-slate-400" />
          <span>FFmpeg Engine:</span>
          <span className={`status-dot ${health.ffmpeg_installed ? 'online' : 'offline'}`} />
          <span style={{ color: health.ffmpeg_installed ? '#10B981' : '#F43F5E', fontWeight: 600 }}>
            {health.ffmpeg_installed ? 'Ready' : 'Missing'}
          </span>
        </div>
      </div>
    </header>
  );
};
