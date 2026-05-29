const API = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface Speaker {
  id: number;
  name: string;
  word_count: number;
  duration: number;
  duration_fmt: string;
  preview: string;
}

export interface PreviewResponse {
  preview_id: string;
  filename: string;
  duration: number;
  word_count: number;
  speakers: Speaker[];
  input_path: string;
}

export interface JobStatus {
  status: "running" | "done" | "error";
  progress: number;
  stage: string;
  logs: string[];
  error: string | null;
}

export interface Clip {
  filename: string;
  duration: string;
  index: number;
}

export async function previewVideo(
  file: File,
  model: string,
  lang: string
): Promise<PreviewResponse> {
  const fd = new FormData();
  fd.append("video", file, file.name);
  fd.append("model", model);
  fd.append("lang", lang);
  const res = await fetch(`${API}/api/preview`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Preview failed");
  }
  return res.json();
}

export async function generateClips(params: {
  input_path: string;
  num_clips: number;
  min_length: number;
  max_length: number;
  subtitle_pos: string;
  model: string;
  lang: string;
  karaoke: boolean;
  show_subtitles: boolean;
  selected_speakers: number[];
  trim_start: number;
  trim_end: number;
  framing: string;
}): Promise<{ job_id: string }> {
  const fd = new FormData();
  Object.entries(params).forEach(([k, v]) => {
    fd.append(k, Array.isArray(v) ? JSON.stringify(v) : String(v));
  });
  const res = await fetch(`${API}/api/generate`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Generate failed");
  }
  return res.json();
}

export async function pollStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API}/api/status/${jobId}`);
  return res.json();
}

export async function fetchResults(jobId: string): Promise<{ clips: Clip[] }> {
  const res = await fetch(`${API}/api/results/${jobId}`);
  return res.json();
}

export function downloadUrl(jobId: string, filename: string) {
  return `${API}/api/download/${jobId}/${encodeURIComponent(filename)}`;
}

export function fmt(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}
