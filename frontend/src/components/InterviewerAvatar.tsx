"use client";

import React, { useEffect, useState } from "react";
import { Sparkles, Volume2, Mic } from "lucide-react";

interface InterviewerAvatarProps {
  isSpeaking: boolean;
  frequencyLevel: number; // 0 to 255 from AnalyserNode
  interviewerName?: string;
  roleTitle?: string;
  currentStage?: string;
}

export default function InterviewerAvatar({
  isSpeaking,
  frequencyLevel,
  interviewerName = "Dr. Elena Vance",
  roleTitle = "Staff Bar-Raiser",
  currentStage = "INTRO",
}: InterviewerAvatarProps) {
  // Normalize frequency for glow intensity (0.15 to 1.0)
  const [glowIntensity, setGlowIntensity] = useState(0.15);

  useEffect(() => {
    if (isSpeaking) {
      const normalized = Math.min(1.0, Math.max(0.3, frequencyLevel / 100));
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
          background: `radial-gradient(circle at center, rgba(59, 130, 246, ${glowIntensity * 0.35}) 0%, transparent 75%)`,
        }}
      />

      {/* Top Bar inside Interviewer Tile */}
      <div className="w-full flex items-center justify-between z-10">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-950/80 backdrop-blur-md border border-slate-800 text-[11px] text-slate-300 font-medium">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>{interviewerName}</span>
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
            width: `${90 + glowIntensity * 28}px`,
            height: `${90 + glowIntensity * 28}px`,
            backgroundColor: "rgba(59, 130, 246, 0.2)",
            filter: "blur(12px)",
            transform: `scale(${1 + glowIntensity * 0.2})`,
          }}
        />

        <div
          className="absolute rounded-full transition-all duration-100"
          style={{
            width: "90px",
            height: "90px",
            boxShadow: isSpeaking
              ? `0 0 ${16 + glowIntensity * 25}px rgba(99, 102, 241, ${0.7 + glowIntensity * 0.3})`
              : "0 0 10px rgba(71, 85, 105, 0.3)",
            border: isSpeaking
              ? "3px solid rgb(96, 165, 250)"
              : "2px solid rgb(71, 85, 105)",
          }}
        />

        {/* 2D Portrait / Avatar Canvas */}
        <div className="relative w-20 h-20 rounded-full overflow-hidden bg-gradient-to-tr from-slate-950 via-slate-800 to-indigo-950 flex items-center justify-center z-10 border border-slate-700/60 shadow-inner">
          <svg
            className="w-16 h-16 text-slate-300 mt-2"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>

          {/* Real-time speaking status pill */}
          {isSpeaking && (
            <div className="absolute bottom-1 px-1.5 py-0.5 rounded-full bg-blue-600/95 text-white text-[9px] font-bold flex items-center gap-1 shadow-md animate-pulse">
              <Volume2 className="w-2.5 h-2.5" /> Speaking
            </div>
          )}
        </div>
      </div>

      {/* Bottom Bar inside Interviewer Tile */}
      <div className="w-full flex items-center justify-between text-xs text-slate-400 z-10 pt-1 border-t border-slate-800/60">
        <span className="font-semibold text-slate-300 text-[11px]">{roleTitle}</span>
        <div className="flex items-center gap-1 text-[10px] text-slate-400">
          <Mic className={`w-3 h-3 ${isSpeaking ? "text-blue-400 animate-pulse" : "text-slate-500"}`} />
          <span>{isSpeaking ? "Voice Active" : "Listening"}</span>
        </div>
      </div>
    </div>
  );
}
