export interface SceneQualityReport {
  scene_id: number;
  visual_type: string;
  render_success: boolean;
  audio_duration: number;
  video_duration: number;
  duration_mismatch: number;
  retry_count: number;
  used_fallback: boolean;
  error_message?: string | null;
}

export interface QualityReport {
  topic: string;
  language: string;
  total_scenes: number;
  successful_scenes: number;
  overall_success_rate: number;
  avg_duration_mismatch: number;
  hallucination_detected: boolean;
  unsupported_claims: string[];
  scenes: SceneQualityReport[];
}

export interface JobResult {
  status: string;
  session_id: string;
  topic: string;
  video_path: string;
  script_path: string;
  quality_report_path: string;
  quality_report: QualityReport;
  duration_seconds: number;
}

export interface JobStatus {
  job_id: string;
  topic: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  result?: JobResult | null;
  error?: string | null;
}

export interface GenerateRequest {
  topic: string;
  input_text?: string;
  pdf_filename?: string;
  language: "en" | "hi";
  target_audience: string;
}

export interface SystemHealth {
  status: string;
  ffmpeg_installed: boolean;
  ollama_running: boolean;
}
