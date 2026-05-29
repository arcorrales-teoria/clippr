"use client";

import { useCallback, useRef, useState } from "react";
import VideoTrimmer from "@/components/VideoTrimmer";
import SpeakersPanel from "@/components/SpeakersPanel";
import SettingsPanel from "@/components/SettingsPanel";
import ProgressPanel from "@/components/ProgressPanel";
import OutputGrid from "@/components/OutputGrid";
import {
  previewVideo,
  generateClips,
  pollStatus,
  fetchResults,
  downloadUrl,
  type PreviewResponse,
  type JobStatus,
  type Clip,
  fmt,
} from "@/lib/api";

type Stage = "idle" | "uploading" | "previewed" | "generating" | "done" | "error";

interface Settings {
  numClips: number;
  minLength: number;
  maxLength: number;
  subtitlePos: "top" | "middle" | "bottom";
  model: string;
  lang: string;
  subtitleLang: string;
  karaoke: boolean;
  showSubtitles: boolean;
  framing: "auto" | "active";
}

const DEFAULT_SETTINGS: Settings = {
  numClips: 3,
  minLength: 30,
  maxLength: 60,
  subtitlePos: "bottom",
  model: "small",
  lang: "es",
  subtitleLang: "es",
  karaoke: true,
  showSubtitles: true,
  framing: "auto",
};

export default function Page() {
  const [stage, setStage] = useState<Stage>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [selectedSpeakers, setSelectedSpeakers] = useState<number[]>([]);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);
  const [saveDir, setSaveDir] = useState<FileSystemDirectoryHandle | null>(null);
  const [saveDirName, setSaveDirName] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasDirPicker = typeof window !== "undefined" && "showDirectoryPicker" in window;

  const processFile = useCallback(async (f: File) => {
    setFile(f);
    setStage("uploading");
    setErrorMsg("");
    setPreview(null);
    setClips([]);
    try {
      const result = await previewVideo(f, settings.model, settings.lang);
      setPreview(result);
      setTrimStart(0);
      setTrimEnd(result.duration);
      setSelectedSpeakers(result.speakers.map((s) => s.id));
      setStage("previewed");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  }, [settings.model, settings.lang]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) processFile(f);
    },
    [processFile]
  );

  const pickSaveDir = async () => {
    try {
      const handle = await (window as unknown as { showDirectoryPicker: (opts?: object) => Promise<FileSystemDirectoryHandle> }).showDirectoryPicker({
        mode: "readwrite",
        startIn: "videos",
      });
      setSaveDir(handle);
      setSaveDirName(handle.name);
    } catch {
      // user cancelled — leave existing selection
    }
  };

  const saveClipsToDir = async (dirHandle: FileSystemDirectoryHandle, readyClips: Clip[], jId: string) => {
    setSaving(true);
    try {
      for (const clip of readyClips) {
        const url = downloadUrl(jId, clip.filename);
        const res = await fetch(url);
        const blob = await res.blob();
        const fileHandle = await dirHandle.getFileHandle(clip.filename, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(blob);
        await writable.close();
      }
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    if (!preview) return;

    // Ask for save location before starting (if API is available and no dir chosen yet)
    let dir = saveDir;
    if (hasDirPicker && !dir) {
      try {
        const handle = await (window as unknown as { showDirectoryPicker: (opts?: object) => Promise<FileSystemDirectoryHandle> }).showDirectoryPicker({
          mode: "readwrite",
          startIn: "videos",
        });
        dir = handle;
        setSaveDir(handle);
        setSaveDirName(handle.name);
      } catch {
        return; // user cancelled picker — don't start
      }
    }

    setStage("generating");
    setClips([]);
    try {
      const { job_id } = await generateClips({
        input_path: preview.input_path,
        num_clips: settings.numClips,
        min_length: settings.minLength,
        max_length: settings.maxLength,
        subtitle_pos: settings.subtitlePos,
        model: settings.model,
        lang: settings.lang,
        karaoke: settings.karaoke,
        show_subtitles: settings.showSubtitles,
        selected_speakers: selectedSpeakers,
        trim_start: trimStart,
        trim_end: trimEnd,
        framing: settings.framing,
      });
      setJobId(job_id);

      // Poll for status
      const poll = async () => {
        const s = await pollStatus(job_id);
        setJobStatus(s);
        if (s.status === "running") {
          setTimeout(poll, 2000);
        } else if (s.status === "done") {
          const { clips } = await fetchResults(job_id);
          setClips(clips);
          setStage("done");
          // Auto-save to chosen directory
          if (dir) saveClipsToDir(dir, clips, job_id);
        } else {
          setErrorMsg(s.error || "Generation failed");
          setStage("error");
        }
      };
      poll();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setStage("error");
    }
  };

  const toggleSpeaker = (id: number) => {
    setSelectedSpeakers((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleTrimChange = useCallback((start: number, end: number) => {
    setTrimStart(start);
    setTrimEnd(end);
  }, []);

  const isGenerating = stage === "generating";
  const canGenerate = stage === "previewed" || stage === "done" || stage === "error";

  return (
    <div className="min-h-screen bg-[#0f0f13] text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-sm font-bold">
            ⚡
          </div>
          <span className="text-lg font-bold tracking-tight">clippr</span>
        </div>
        <p className="text-xs text-zinc-500">AI-powered vertical clips, locally.</p>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Upload zone */}
        {(stage === "idle" || stage === "uploading") && (
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative rounded-2xl border-2 border-dashed transition-all cursor-pointer overflow-hidden
              ${isDragging
                ? "border-purple-500 bg-purple-500/10"
                : "border-zinc-700 hover:border-zinc-600 hover:bg-zinc-900/50"
              }
              ${stage === "uploading" ? "pointer-events-none opacity-70" : ""}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.mov,.mkv,video/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0])}
            />
            <div className="flex flex-col items-center gap-3 py-16 px-8 text-center">
              {stage === "uploading" ? (
                <>
                  <div className="w-10 h-10 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
                  <p className="text-sm text-zinc-400">Analyzing video…</p>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-2xl bg-zinc-800 flex items-center justify-center">
                    <svg className="w-7 h-7 text-zinc-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.888L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">Drop your video here or click to browse</p>
                    <p className="text-xs text-zinc-500 mt-1">.mp4 · .mov · .mkv</p>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Previewed / generating / done */}
        {stage !== "idle" && stage !== "uploading" && file && preview && (
          <div className="space-y-6">
            {/* File info bar */}
            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-800">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.888L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                  </svg>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-white truncate">{preview.filename}</p>
                  <p className="text-xs text-zinc-500">{fmt(preview.duration)} · {preview.word_count} words</p>
                </div>
              </div>
              <button
                onClick={() => { setStage("idle"); setFile(null); setPreview(null); }}
                className="btn-icon flex-shrink-0 ml-3"
              >
                Change
              </button>
            </div>

            {/* Video trimmer */}
            <section className="rounded-2xl bg-zinc-900 border border-zinc-800 p-5 space-y-4">
              <h2 className="text-sm font-semibold text-white">Trim Range</h2>
              <VideoTrimmer
                file={file}
                duration={preview.duration}
                trimStart={trimStart}
                trimEnd={trimEnd}
                onChange={handleTrimChange}
              />
            </section>

            {/* Speakers + settings */}
            <section className="rounded-2xl bg-zinc-900 border border-zinc-800 p-5 space-y-6">
              <SpeakersPanel
                speakers={preview.speakers}
                selected={selectedSpeakers}
                onToggle={toggleSpeaker}
              />
              <div className={preview.speakers.length ? "pt-2 border-t border-zinc-800" : ""}>
                <SettingsPanel settings={settings} onChange={setSettings} />
              </div>
            </section>

            {/* Progress panel */}
            {(isGenerating || stage === "done" || (stage === "error" && jobStatus)) && jobStatus && (
              <section className="rounded-2xl bg-zinc-900 border border-zinc-800 p-5 space-y-4">
                <h2 className="text-sm font-semibold text-white">Progress</h2>
                <ProgressPanel status={jobStatus} />
              </section>
            )}

            {/* Output grid */}
            {stage === "done" && jobId && clips.length > 0 && (
              <section className="rounded-2xl bg-zinc-900 border border-zinc-800 p-5">
                <OutputGrid jobId={jobId} clips={clips} />
              </section>
            )}

            {/* Error */}
            {stage === "error" && errorMsg && (
              <div className="rounded-xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
                {errorMsg}
              </div>
            )}

            {/* Save location */}
            {hasDirPicker && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-zinc-900 border border-zinc-800">
                <svg className="w-4 h-4 text-zinc-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-zinc-500">Save to</p>
                  <p className="text-sm text-white truncate">
                    {saveDirName ? saveDirName : <span className="text-zinc-500 italic">No folder selected</span>}
                  </p>
                </div>
                <button onClick={pickSaveDir} className="btn-icon flex-shrink-0">
                  {saveDirName ? "Change" : "Choose folder"}
                </button>
              </div>
            )}

            {/* Saving indicator */}
            {saving && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-sm text-emerald-400">
                <span className="w-3.5 h-3.5 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin flex-shrink-0" />
                Saving clips to <span className="font-medium">{saveDirName}</span>…
              </div>
            )}

            {/* Generate CTA */}
            <button
              onClick={handleGenerate}
              disabled={!canGenerate || isGenerating || selectedSpeakers.length === 0}
              className="btn btn-primary w-full py-4 text-base font-semibold tracking-wide gap-2"
            >
              {isGenerating ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  Generating…
                </>
              ) : (
                "✦ Generate Clips"
              )}
            </button>
          </div>
        )}

        {/* Error without preview */}
        {stage === "error" && !preview && (
          <div className="rounded-xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
            {errorMsg}
            <button
              className="ml-3 underline text-red-300 hover:text-red-200"
              onClick={() => setStage("idle")}
            >
              Try again
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
