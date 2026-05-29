"use client";

import { Speaker } from "@/lib/api";

interface Props {
  speakers: Speaker[];
  selected: number[];
  onToggle: (id: number) => void;
}

export default function SpeakersPanel({ speakers, selected, onToggle }: Props) {
  if (!speakers.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-zinc-400 uppercase tracking-widest">Speakers</p>
      <div className="space-y-2">
        {speakers.map((sp) => {
          const isSelected = selected.includes(sp.id);
          return (
            <button
              key={sp.id}
              onClick={() => onToggle(sp.id)}
              data-selected={isSelected}
              className="btn w-full text-left rounded-xl px-4 py-3"
            >
              <div className="flex items-center gap-3">
                {/* Checkbox */}
                <div
                  className={`w-4 h-4 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                    isSelected ? "border-purple-500 bg-purple-500" : "border-zinc-600"
                  }`}
                >
                  {isSelected && (
                    <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none">
                      <path d="M1.5 5L4 7.5L8.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>

                {/* Speaker info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-white truncate">{sp.name}</span>
                    <div className="flex items-center gap-2 flex-shrink-0 text-xs text-zinc-500">
                      <span>{sp.word_count} words</span>
                      <span>·</span>
                      <span>{sp.duration_fmt}</span>
                    </div>
                  </div>
                  {sp.preview && (
                    <p className="mt-0.5 text-xs text-zinc-500 italic truncate">
                      &ldquo;{sp.preview}&rdquo;
                    </p>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
