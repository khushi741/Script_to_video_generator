import { GenerateRequest, JobStatus, SystemHealth } from './types';

const API_BASE = (import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : '') + '/api';

export async function checkSystemHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (err) {
    return {
      status: 'offline',
      ffmpeg_installed: false,
      ollama_running: false,
    };
  }
}

export async function uploadPdf(file: File): Promise<{ filename: string; path: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/upload-pdf`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to upload PDF');
  }

  return await res.json();
}

export async function startVideoGeneration(req: GenerateRequest): Promise<string> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to start video generation');
  }

  const data = await res.json();
  return data.job_id;
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/status/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch job status: ${res.statusText}`);
  }
  return await res.json();
}

export function getVideoDownloadUrl(jobId: string): string {
  return `${API_BASE}/video/${jobId}`;
}
