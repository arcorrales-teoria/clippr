"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { fmt } from "@/lib/api";

interface Props {
  file: File;
  duration: number;
  trimStart: number;
  trimEnd: number;
  onChange: (start: number, end: number) => void;
}

export default function VideoTrimmer({ file, duration, trimStart, trimEnd, onChange }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const objectUrlRef = useRef<string | null>(null);

  const [dragging, setDragging] = useState<"start" | "end" | "range" | null>(null);
  const dragStartX = useRef(0);
  const dragStartValues = useRef({ start: 0, end: 0 });

  // Create object URL once
  useEffect(() => {
    const url = URL.createObjectURL(file);
    objectUrlRef.current = url;
    if (videoRef.current) videoRef.current.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Seek video when trimStart changes
  useEffect(() => {
    if (videoRef.current) videoRef.current.currentTime = trimStart;
  }, [trimStart]);

  const posToTime = useCallback(
    (clientX: number): number => {
      const rect = trackRef.current!.getBoundingClientRect();
      const frac = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
      return frac * duration;
    },
    [duration]
  );

  const onMouseDown = useCallback(
    (e: React.MouseEvent, handle: "start" | "end" | "range") => {
      e.preventDefault();
      setDragging(handle);
      dragStartX.current = e.clientX;
      dragStartValues.current = { start: trimStart, end: trimEnd };
    },
    [trimStart, trimEnd]
  );

  useEffect(() => {
    if (!dragging) return;

    const onMove = (e: MouseEvent) => {
      const rect = trackRef.current!.getBoundingClientRect();
      const dt = ((e.clientX - dragStartX.current) / rect.width) * duration;

      if (dragging === "start") {
        const newStart = Math.max(0, Math.min(dragStartValues.current.start + dt, trimEnd - 5));
        onChange(newStart, trimEnd);
      } else if (dragging === "end") {
        const newEnd = Math.min(duration, Math.max(dragStartValues.current.end + dt, trimStart + 5));
        onChange(trimStart, newEnd);
      } else {
        const selLen = dragStartValues.current.end - dragStartValues.current.start;
        let newStart = dragStartValues.current.start + dt;
        newStart = Math.max(0, Math.min(newStart, duration - selLen));
        onChange(newStart, newStart + selLen);
      }
    };

    const onUp = () => setDragging(null);

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging, duration, trimStart, trimEnd, onChange]);

  const startPct = (trimStart / duration) * 100;
  const endPct = (trimEnd / duration) * 100;
  const selected = trimEnd - trimStart;

  return (
    <div className="space-y-3">
      {/* Video preview */}
      <div className="relative rounded-xl overflow-hidden bg-black aspect-video">
        <video
          ref={videoRef}
          className="w-full h-full object-contain"
          muted
          playsInline
          controls
        />
      </div>

      {/* Trim labels */}
      <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
        <span>
          In{" "}
          <span className="text-white font-semibold">{fmt(trimStart)}</span>
        </span>
        <span>
          <span className="text-purple-400 font-semibold">{fmt(selected)}</span>{" "}
          selected
        </span>
        <span>
          Out{" "}
          <span className="text-white font-semibold">{fmt(trimEnd)}</span>
        </span>
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className="relative h-10 rounded-lg bg-zinc-800 cursor-pointer select-none"
      >
        {/* Full timeline ticks */}
        <div className="absolute inset-0 flex items-end pb-1 px-1 pointer-events-none">
          {Array.from({ length: Math.floor(duration / 10) + 1 }).map((_, i) => (
            <div
              key={i}
              className="absolute bottom-1 w-px h-2 bg-zinc-600"
              style={{ left: `${(i * 10 / duration) * 100}%` }}
            />
          ))}
        </div>

        {/* Dimmed regions outside selection */}
        <div
          className="absolute inset-y-0 left-0 bg-zinc-900/70 rounded-l-lg pointer-events-none"
          style={{ width: `${startPct}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-zinc-900/70 rounded-r-lg pointer-events-none"
          style={{ width: `${100 - endPct}%` }}
        />

        {/* Selected range (draggable) */}
        <div
          className="absolute inset-y-0 bg-purple-600/30 border-y-2 border-purple-500 cursor-grab active:cursor-grabbing"
          style={{ left: `${startPct}%`, width: `${endPct - startPct}%` }}
          onMouseDown={(e) => onMouseDown(e, "range")}
        />

        {/* Start handle */}
        <div
          className="absolute inset-y-0 flex items-center justify-center cursor-ew-resize z-10"
          style={{ left: `${startPct}%`, width: "16px", transform: "translateX(-50%)" }}
          onMouseDown={(e) => onMouseDown(e, "start")}
        >
          <div className="w-3 h-8 bg-purple-500 rounded-sm flex items-center justify-center shadow-lg">
            <div className="flex flex-col gap-0.5">
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
            </div>
          </div>
        </div>

        {/* End handle */}
        <div
          className="absolute inset-y-0 flex items-center justify-center cursor-ew-resize z-10"
          style={{ left: `${endPct}%`, width: "16px", transform: "translateX(-50%)" }}
          onMouseDown={(e) => onMouseDown(e, "end")}
        >
          <div className="w-3 h-8 bg-purple-500 rounded-sm flex items-center justify-center shadow-lg">
            <div className="flex flex-col gap-0.5">
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
              <div className="w-0.5 h-1 bg-purple-200 rounded" />
            </div>
          </div>
        </div>
      </div>

      <p className="text-xs text-zinc-500 text-center">
        Drag handles to select the region to use for clip generation
      </p>
    </div>
  );
}
