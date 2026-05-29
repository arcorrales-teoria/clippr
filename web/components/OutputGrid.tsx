"use client";

import { Clip, downloadUrl } from "@/lib/api";

interface Props {
  jobId: string;
  clips: Clip[];
}

export default function OutputGrid({ jobId, clips }: Props) {
  if (!clips.length) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
        {clips.length} Clip{clips.length !== 1 ? "s" : ""} Ready
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {clips.map((clip) => {
          const url = downloadUrl(jobId, clip.filename);
          return (
            <div
              key={clip.index}
              className="group rounded-xl overflow-hidden border border-zinc-800 bg-zinc-900 hover:border-zinc-700 transition-all"
            >
              {/* Thumbnail — video preview */}
              <div className="relative aspect-[9/16] bg-zinc-950 overflow-hidden">
                <video
                  src={url}
                  className="w-full h-full object-cover"
                  muted
                  playsInline
                  loop
                  onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play()}
                  onMouseLeave={(e) => {
                    const v = e.currentTarget as HTMLVideoElement;
                    v.pause();
                    v.currentTime = 0;
                  }}
                />
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                  <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                    <svg className="w-4 h-4 text-white translate-x-0.5" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M3 2l10 6-10 6V2z" />
                    </svg>
                  </div>
                </div>
                <div className="absolute bottom-1.5 right-1.5 bg-black/70 backdrop-blur-sm text-white text-xs px-1.5 py-0.5 rounded font-mono">
                  {clip.duration}
                </div>
              </div>

              {/* Info + download */}
              <div className="p-2.5 space-y-2">
                <p className="text-xs text-zinc-400 truncate" title={clip.filename}>
                  {clip.filename}
                </p>
                <a
                  href={url}
                  download={clip.filename}
                  className="btn w-full gap-1.5"
                >
                  <svg className="w-3 h-3" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M8 2v8M4 7l4 4 4-4M2 13h12" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Download
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
