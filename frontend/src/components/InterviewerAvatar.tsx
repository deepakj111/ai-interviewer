"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, Volume2, Mic, Pause, Radio } from "lucide-react";
import { InterviewerPersona } from "@/lib/voiceManager";

interface InterviewerAvatarProps {
  isSpeaking: boolean;
  frequencyLevel: number; // 0 to 255
  persona?: InterviewerPersona;
  targetCompany?: string;
  currentStage?: string;
  isCandidateWorking?: boolean;
}

export default function InterviewerAvatar({
  isSpeaking,
  frequencyLevel,
  persona,
  targetCompany = "Top Tech",
  currentStage = "INTRO",
  isCandidateWorking = false,
}: InterviewerAvatarProps) {
  const [glowIntensity, setGlowIntensity] = useState(0.15);

  const name = persona?.name || "Dr. Elena Vance";
  const title = persona?.title || "Principal Bar-Raiser";
  const isMale = persona?.gender === "male";

  useEffect(() => {
    if (isSpeaking) {
      const normalized = Math.min(1.0, Math.max(0.3, frequencyLevel / 80));
      setGlowIntensity(normalized);
    } else {
      setGlowIntensity(0.15);
    }
  }, [isSpeaking, frequencyLevel]);

  return (
    <div className="relative flex flex-col items-center justify-between p-4 rounded-2xl glass-panel border border-slate-800 bg-slate-900/90 shadow-2xl overflow-hidden shrink-0 w-full max-w-md mx-auto aspect-[16/10]">
      {/* Background radial gradient reacting to voice */}
      <div
        className="absolute inset-0 transition-opacity duration-300 pointer-events-none"
        style={{
          background: `radial-gradient(circle at center, rgba(59, 130, 246, ${glowIntensity * 0.4}) 0%, transparent 75%)`,
        }}
      />

      {/* Top Bar inside Interviewer Tile */}
      <div className="w-full flex items-center justify-between z-10">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-950/80 backdrop-blur-md border border-slate-800 text-[11px] text-slate-200 font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>{name}</span>
          <span className="text-[10px] text-slate-400 font-normal">({targetCompany})</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-950/80 backdrop-blur-md border border-blue-800/50 text-[10px] text-blue-300 font-semibold uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
          <span>{currentStage.replace(/_/g, " ")}</span>
        </div>
      </div>

      {/* Glowing Pulsing Ring & Avatar Canvas */}
      <div className="relative my-auto flex items-center justify-center">
        {/* Dynamic aura rings */}
        <div
          className="absolute rounded-full transition-all duration-150"
          style={{
            width: `${100 + glowIntensity * 32}px`,
            height: `${100 + glowIntensity * 32}px`,
            backgroundColor: "rgba(59, 130, 246, 0.22)",
            filter: "blur(14px)",
            transform: `scale(${1 + glowIntensity * 0.25})`,
          }}
        />

        <div
          className="absolute rounded-full transition-all duration-100"
          style={{
            width: "96px",
            height: "96px",
            boxShadow: isSpeaking
              ? `0 0 ${20 + glowIntensity * 30}px rgba(99, 102, 241, ${0.7 + glowIntensity * 0.3})`
              : "0 0 12px rgba(71, 85, 105, 0.35)",
            border: isSpeaking
              ? "3px solid rgb(96, 165, 250)"
              : "2px solid rgb(71, 85, 105)",
          }}
        />

        {/* Professional Stylized Avatar Portrait */}
        <div className="relative w-24 h-24 rounded-full overflow-hidden bg-gradient-to-tr from-slate-950 via-slate-800 to-indigo-950 flex items-center justify-center z-10 border border-slate-700/60 shadow-inner">
          <svg
            className="w-20 h-20 text-slate-200 mt-2"
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Professional Blazer & Shirt */}
            <path
              d="M15 95 C15 75, 30 65, 50 65 C70 65, 85 75, 85 95 Z"
              fill={isMale ? "#1e293b" : "#0f172a"}
              stroke="#334155"
              strokeWidth="2"
            />
            <path
              d="M40 65 L50 82 L60 65 Z"
              fill="#f8fafc"
            />
            {/* Tech Lanyard / Badge */}
            <path
              d="M38 65 L48 95 L52 95 L62 65"
              stroke="#3b82f6"
              strokeWidth="2.5"
            />
            <rect
              x="45"
              y="85"
              width="10"
              height="10"
              rx="2"
              fill="#2563eb"
            />
            {/* Neck */}
            <rect
              x="43"
              y="50"
              width="14"
              height="18"
              rx="4"
              fill="#e2e8f0"
            />
            {/* Face */}
            <ellipse
              cx="50"
              cy="42"
              rx="18"
              ry="21"
              fill="#f1f5f9"
            />
            {/* Hair */}
            {isMale ? (
              <path
                d="M31 35 C31 20, 69 20, 69 35 C68 25, 32 25, 31 35 Z"
                fill="#334155"
              />
            ) : (
              <path
                d="M28 42 C26 22, 74 22, 72 42 C76 56, 73 62, 73 62 C69 50, 71 34, 50 32 C29 34, 31 50, 27 62 Z"
                fill="#334155"
              />
            )}
            {/* Glasses for intellectual bar-raiser aesthetic */}
            <rect
              x="36"
              y="38"
              width="11"
              height="8"
              rx="2"
              stroke="#0f172a"
              strokeWidth="1.5"
              fill="rgba(255,255,255,0.4)"
            />
            <rect
              x="53"
              y="38"
              width="11"
              height="8"
              rx="2"
              stroke="#0f172a"
              strokeWidth="1.5"
              fill="rgba(255,255,255,0.4)"
            />
            <line
              x1="47"
              y1="42"
              x2="53"
              y2="42"
              stroke="#0f172a"
              strokeWidth="1.5"
            />
            {/* Eyes */}
            <circle cx="41.5" cy="42" r="1.5" fill="#0f172a" />
            <circle cx="58.5" cy="42" r="1.5" fill="#0f172a" />
            {/* Subtle smile / professional composure */}
            <path
              d="M45 54 Q50 57 55 54"
              stroke="#64748b"
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
            />
          </svg>

          {/* Animated sound wave bars when speaking */}
          {isSpeaking && (
            <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] flex items-center justify-center gap-1 z-20">
              <span className="w-1 h-4 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <span className="w-1 h-7 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <span className="w-1 h-5 bg-sky-400 rounded-full animate-bounce" />
              <span className="w-1 h-8 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
              <span className="w-1 h-4 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.35s]" />
            </div>
          )}
        </div>
      </div>

      {/* Bottom Bar: Status Pill & Persona Role */}
      <div className="w-full flex items-center justify-between z-10 pt-2 border-t border-slate-800/60">
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-slate-200">{title}</span>
          <span className="text-[9px] text-blue-400 font-medium">Bar-Raiser Interviewer</span>
        </div>

        {/* Real-time speaking / listening indicator */}
        {isSpeaking ? (
          <div className="px-2.5 py-1 rounded-full bg-blue-600/95 text-white text-[10px] font-bold flex items-center gap-1.5 shadow-md shadow-blue-500/20 animate-pulse">
            <Volume2 className="w-3 h-3" /> Speaking
          </div>
        ) : isCandidateWorking ? (
          <div className="px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[10px] font-semibold flex items-center gap-1.5">
            <Pause className="w-3 h-3 text-amber-400" /> Holding (Typing)
          </div>
        ) : (
          <div className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] font-semibold flex items-center gap-1.5">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" /> Listening
          </div>
        )}
      </div>
    </div>
  );
}
