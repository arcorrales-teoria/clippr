"use client";

import { useState } from "react";

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

interface Props {
  settings: Settings;
  onChange: (s: Settings) => void;
}

const LANGUAGES = [
  { code: "es", label: "Spanish" },
  { code: "en", label: "English" },
  { code: "pt", label: "Portuguese" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "ja", label: "Japanese" },
  { code: "zh", label: "Chinese" },
  { code: "ko", label: "Korean" },
  { code: "ar", label: "Arabic" },
];

const MODELS: { value: string; label: string; desc: string }[] = [
  { value: "tiny",   label: "Tiny",   desc: "Fastest, lower accuracy" },
  { value: "base",   label: "Base",   desc: "Fast, basic accuracy" },
  { value: "small",  label: "Small",  desc: "Balanced (recommended)" },
  { value: "medium", label: "Medium", desc: "Slower, higher accuracy" },
  { value: "large",  label: "Large",  desc: "Slowest, best accuracy" },
];

const POS_OPTIONS: { value: Settings["subtitlePos"]; label: string; icon: React.ReactNode }[] = [
  {
    value: "top", label: "Top",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4">
        <rect x="3" y="3" width="14" height="3" rx="1" fill="currentColor" opacity="0.8" />
        <rect x="3" y="8" width="14" height="9" rx="1" fill="currentColor" opacity="0.15" />
      </svg>
    ),
  },
  {
    value: "middle", label: "Middle",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4">
        <rect x="3" y="2" width="14" height="16" rx="1" fill="currentColor" opacity="0.15" />
        <rect x="3" y="8.5" width="14" height="3" rx="1" fill="currentColor" opacity="0.8" />
      </svg>
    ),
  },
  {
    value: "bottom", label: "Bottom",
    icon: (
      <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4">
        <rect x="3" y="3" width="14" height="9" rx="1" fill="currentColor" opacity="0.15" />
        <rect x="3" y="14" width="14" height="3" rx="1" fill="currentColor" opacity="0.8" />
      </svg>
    ),
  },
];

export default function SettingsPanel({ settings, onChange }: Props) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const set = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    onChange({ ...settings, [key]: value });

  // When video language changes, sync subtitle language if they were the same
  const setLang = (code: string) => {
    const wasLinked = settings.lang === settings.subtitleLang;
    onChange({ ...settings, lang: code, subtitleLang: wasLinked ? code : settings.subtitleLang });
  };

  return (
    <div className="space-y-5">

      {/* Video Language */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">
          Video Language
        </label>
        <div className="relative">
          <select
            value={settings.lang}
            onChange={(e) => setLang(e.target.value)}
            className="w-full h-9 bg-zinc-800 border border-zinc-700 rounded-lg pl-3 pr-8 text-sm text-white focus:outline-none focus:border-purple-500 appearance-none cursor-pointer"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </select>
          <ChevronIcon />
        </div>
      </div>

      {/* Transcription Model + Subtitle Language — side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">
              Transcription Model
            </label>
            <Tooltip text="Whisper AI model used to transcribe speech. Larger models are more accurate but take longer to process. 'Small' is the best trade-off for most videos.">
              <span className="w-4 h-4 rounded-full bg-zinc-700 flex items-center justify-center text-zinc-400 text-[10px] font-bold leading-none cursor-help flex-shrink-0">?</span>
            </Tooltip>
          </div>
          <div className="relative">
            <select
              value={settings.model}
              onChange={(e) => set("model", e.target.value)}
              className="w-full h-9 bg-zinc-800 border border-zinc-700 rounded-lg pl-3 pr-8 text-sm text-white focus:outline-none focus:border-purple-500 appearance-none cursor-pointer"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label} — {m.desc}</option>
              ))}
            </select>
            <ChevronIcon />
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">
              Subtitle Language
            </label>
            <Tooltip text="Language used for the burned-in subtitles. Defaults to the video language. Change this if you want captions in a different language.">
              <span className="w-4 h-4 rounded-full bg-zinc-700 flex items-center justify-center text-zinc-400 text-[10px] font-bold leading-none cursor-help flex-shrink-0">?</span>
            </Tooltip>
          </div>
          <div className="relative">
            <select
              value={settings.subtitleLang}
              onChange={(e) => set("subtitleLang", e.target.value)}
              className="w-full h-9 bg-zinc-800 border border-zinc-700 rounded-lg pl-3 pr-8 text-sm text-white focus:outline-none focus:border-purple-500 appearance-none cursor-pointer"
            >
              <option value={settings.lang}>
                {LANGUAGES.find((l) => l.code === settings.lang)?.label ?? settings.lang} (Video language)
              </option>
              {LANGUAGES.filter((l) => l.code !== settings.lang).map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
            <ChevronIcon />
          </div>
        </div>
      </div>

      {/* Framing */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest">Framing</label>
        <div className="grid grid-cols-2 gap-2">
          {(["auto", "active"] as const).map((v) => (
            <button
              key={v}
              onClick={() => set("framing", v)}
              data-selected={settings.framing === v}
              className="btn w-full"
            >
              {v === "auto" ? "Auto reframe" : "Active speaker"}
            </button>
          ))}
        </div>
      </div>

      {/* Clips / lengths */}
      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">Clips</label>
          <div className="flex items-center gap-1">
            <button onClick={() => set("numClips", Math.max(1, settings.numClips - 1))} className="btn-icon w-7 h-8">−</button>
            <div className="flex-1 h-8 bg-zinc-800 border border-zinc-700 rounded-lg flex items-center justify-center text-sm font-medium text-white">
              {settings.numClips}
            </div>
            <button onClick={() => set("numClips", Math.min(20, settings.numClips + 1))} className="btn-icon w-7 h-8">+</button>
          </div>
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">Min (s)</label>
          <input
            type="number" min={5} max={settings.maxLength} value={settings.minLength}
            onChange={(e) => set("minLength", parseInt(e.target.value) || 5)}
            className="w-full h-8 bg-zinc-800 border border-zinc-700 rounded-lg px-2 text-sm text-white focus:outline-none focus:border-purple-500"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest block">Max (s)</label>
          <input
            type="number" min={settings.minLength} max={300} value={settings.maxLength}
            onChange={(e) => set("maxLength", parseInt(e.target.value) || 60)}
            className="w-full h-8 bg-zinc-800 border border-zinc-700 rounded-lg px-2 text-sm text-white focus:outline-none focus:border-purple-500"
          />
        </div>
      </div>

      {/* Caption position */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-zinc-400 uppercase tracking-widest">Caption Position</label>
        <div className="grid grid-cols-3 gap-2">
          {POS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => set("subtitlePos", opt.value)}
              data-selected={settings.subtitlePos === opt.value}
              className="btn w-full flex-col gap-1.5 py-3"
            >
              {opt.icon}
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Settings (collapsible) */}
      <div className="border border-zinc-800 rounded-xl overflow-hidden">
        <button
          onClick={() => setAdvancedOpen((o) => !o)}
          className="toggle-switch w-full flex items-center justify-between px-4 py-3 hover:bg-zinc-800/50 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
              Advanced Settings
            </span>
            <Tooltip text="Control caption rendering behavior. These settings affect how subtitles look and animate. Most users can leave them as default.">
              <span className="w-4 h-4 rounded-full bg-zinc-700 flex items-center justify-center text-zinc-400 text-[10px] font-bold leading-none cursor-help">?</span>
            </Tooltip>
          </div>
          <svg
            className={`w-4 h-4 text-zinc-500 transition-transform duration-200 ${advancedOpen ? "rotate-180" : ""}`}
            viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"
          >
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {advancedOpen && (
          <div className="px-4 pb-4 pt-3 space-y-4 border-t border-zinc-800">
            <AdvancedToggle
              label="Subtitles"
              description="Burn text captions into the video so viewers can read along without sound."
              checked={settings.showSubtitles}
              onChange={(v) => set("showSubtitles", v)}
            />
            <AdvancedToggle
              label="Karaoke highlight"
              description="Each word lights up in yellow as it's spoken, following the audio in real time — like karaoke. Requires subtitles to be on."
              checked={settings.karaoke}
              disabled={!settings.showSubtitles}
              onChange={(v) => set("karaoke", v)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function ChevronIcon() {
  return (
    <div className="pointer-events-none absolute inset-y-0 right-2.5 flex items-center">
      <svg className="w-3.5 h-3.5 text-zinc-500" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function AdvancedToggle({
  label, description, checked, disabled, onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`toggle-switch w-full flex items-start gap-3 text-left transition-opacity ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <div className={`mt-0.5 w-9 h-5 flex-shrink-0 rounded-full transition-colors relative ${checked && !disabled ? "bg-purple-600" : "bg-zinc-700"}`}>
        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium leading-5 ${checked && !disabled ? "text-white" : "text-zinc-400"}`}>{label}</p>
        <p className="text-xs text-zinc-500 leading-4 mt-0.5">{description}</p>
      </div>
    </button>
  );
}

function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 z-50 pointer-events-none">
          <div className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-300 leading-relaxed shadow-xl">
            {text}
          </div>
          <div className="w-2 h-2 bg-zinc-800 border-r border-b border-zinc-700 rotate-45 mx-auto -mt-1" />
        </div>
      )}
    </div>
  );
}
