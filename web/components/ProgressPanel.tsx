"use client";

import { useEffect, useRef } from "react";
import { JobStatus } from "@/lib/api";

interface Props {
  status: JobStatus;
}

export default function ProgressPanel({ status }: Props) {
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [status.logs]);

  const isRunning = status.status === "running";
  const isDone = status.status === "done";
  const isError = status.status === "error";

  return (
    <div className="space-y-3">
      {/* Stage + progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className={`font-medium ${isError ? "text-red-400" : "text-zinc-300"}`}>
            {isError ? "Error" : status.stage || "Processing…"}
          </span>
          <span className="text-zinc-500">{Math.round(status.progress)}%</span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isError
                ? "bg-red-500"
                : isDone
                ? "bg-emerald-500"
                : "bg-gradient-to-r from-purple-600 to-blue-500"
            } ${isRunning ? "animate-pulse" : ""}`}
            style={{ width: `${status.progress}%` }}
          />
        </div>
      </div>

      {/* Log stream */}
      <div
        ref={logsRef}
        className="h-40 overflow-y-auto rounded-xl bg-zinc-950 border border-zinc-800 p-3 font-mono text-xs text-zinc-400 space-y-0.5"
      >
        {status.logs.map((line, i) => (
          <div key={i} className="leading-5">
            <span className="text-zinc-600 select-none mr-2">
              {String(i + 1).padStart(2, "0")}
            </span>
            {line}
          </div>
        ))}
        {isRunning && (
          <div className="flex items-center gap-1 text-purple-400">
            <span className="animate-pulse">▌</span>
          </div>
        )}
        {isError && status.error && (
          <div className="text-red-400 mt-1">{status.error}</div>
        )}
      </div>
    </div>
  );
}
