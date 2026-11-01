"use client";

import React, { useEffect, useState } from "react";
import { Mic, Volume2 } from "lucide-react";

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
  roleTitle = "Principal Bar-Raiser",
  currentStage = "INTRO",
}: InterviewerAvatarProps) {
  // Normalize frequency for glow intensity (0.2 to 1.0)
  const [glowIntensity, setGlowIntensity] = useState(0.2);

  useEffect(() => {
    if (isSpeaking) {
      const normalized = Math.min(1.0, Math.max(0.3, frequencyLevel / 120));
      setGlowIntensity(normalized);
    } else {
      setGlowIntensity(0.15);
    }
  }, [isSpeaking, frequencyLevel]);

  return (
    <div className="relative flex flex-col items-center justify-center p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/80 shadow-2xl overflow-hidden">
      {/* Background radial gradient reacting to voice */}
      <div
        className="absolute inset-0 transition-opacity duration-300 pointer-events-none"
        style={{
          background: `radial-gradient(circle at center, rgba(59, 130, 246, ${glowIntensity * 0.35}) 0%, transparent 70%)`,
        }}
      />

      {/* Glowing Pulsing Ring Container */}
      <div className="relative mb-5 flex items-center justify-center">
        {/* Dynamic aura rings */}
        <div
          className="absolute rounded-full transition-all duration-150"
          style={{
            width: `${128 + glowIntensity * 32}px`,
            height: `${128 + glowIntensity * 32}px`,
            backgroundColor: "rgba(59, 130, 246, 0.2)",
            filter: "blur(14px)",
            transform: `scale(${1 + glowIntensity * 0.2})`,
          }}
        />

        <div
          className="absolute rounded-full transition-all duration-100"
          style={{
            width: "128px",
            height: "128px",
            boxShadow: isSpeaking
              ? `0 0 ${20 + glowIntensity * 35}px rgba(99, 102, 241, ${0.6 + glowIntensity * 0.4})`
              : "0 0 10px rgba(71, 85, 105, 0.3)",
            border: isSpeaking
              ? "3px solid rgb(96, 165, 250)"
              : "3px solid rgb(71, 85, 105)",
          }}
        />

        {/* 2D Portrait / Avatar Canvas */}
        <div className="relative w-32 h-32 rounded-full overflow-hidden bg-gradient-to-tr from-slate-950 via-slate-800 to-indigo-950 flex items-center justify-center z-10 border border-slate-700/50">
          {/* Stylized vector SVG avatar */}
          <svg
            className="w-24 h-24 text-slate-300 mt-3"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>

          {/* Real-time speaking wave badge */}
          {isSpeaking && (
            <div className="absolute bottom-2 px-2 py-0.5 rounded-full bg-blue-600/90 text-white text-[10px] font-semibold flex items-center gap-1 shadow-md animate-pulse">
              <Volume2 className="w-3 h-3" /> Speaking
            </div>
          )}
        </div>
      </div>

      {/* Identity & Status */}
      <div className="text-center z-10">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center justify-center gap-2">
          {interviewerName}
        </h3>
        <p className="text-xs text-blue-400 font-medium tracking-wide uppercase mt-0.5">
          {roleTitle}
        </p>

        {/* Stage tag */}
        <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          <span>Stage: {currentStage.replace(/_/g, " ")}</span>
        </div>
      </div>
    </div>
  );
}
