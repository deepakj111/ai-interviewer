"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Sparkles, Volume2, Radio, Pause, Cpu } from "lucide-react";
import { InterviewerPersona } from "@/lib/voiceManager";

interface InterviewerAvatarProps {
  isSpeaking: boolean;
  frequencyLevel: number; // 0 to 100
  persona?: InterviewerPersona;
  targetCompany?: string;
  currentStage?: string;
  isCandidateWorking?: boolean;
  isInterviewerThinking?: boolean;
}

export default function InterviewerAvatar({
  isSpeaking,
  frequencyLevel,
  persona,
  targetCompany = "Top Tech",
  currentStage = "INTRO",
  isCandidateWorking = false,
  isInterviewerThinking = false,
}: InterviewerAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const name = persona?.name || "Dr. Elena Vance";
  const title = persona?.title || "Principal Bar-Raiser";
  const avatarImage = persona?.avatarImage || "/avatars/elena.jpg";
  const archetype = persona?.archetype || "Principal Bar-Raiser";

  // Reactive wave animation on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let phase = 0;
    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const isVoiceActive = isSpeaking || frequencyLevel > 10;
      const amplitude = isVoiceActive ? Math.min(24, Math.max(6, frequencyLevel * 0.28)) : 3;
      phase += isVoiceActive ? 0.08 : 0.02;

      // Draw dual gradient audio wave curves
      const waveColors = isVoiceActive
        ? ["rgba(59, 130, 246, 0.7)", "rgba(99, 102, 241, 0.6)", "rgba(147, 51, 234, 0.5)"]
        : ["rgba(71, 85, 105, 0.3)", "rgba(51, 65, 85, 0.2)"];

      waveColors.forEach((color, idx) => {
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5 - idx * 0.5;

        for (let x = 0; x < width; x += 4) {
          const y =
            height / 2 +
            Math.sin(x * 0.04 + phase + idx * 1.2) *
              amplitude *
              Math.sin((x / width) * Math.PI);
          if (x === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isSpeaking, frequencyLevel]);

  // Derived state indicator
  let stateBadge = {
    label: "Listening",
    icon: Radio,
    badgeClass: "bg-emerald-500/15 border-emerald-500/30 text-emerald-300",
    dotClass: "bg-emerald-400 animate-pulse",
  };

  if (isSpeaking) {
    stateBadge = {
      label: "Speaking",
      icon: Volume2,
      badgeClass: "bg-blue-600/90 border-blue-400 text-white shadow-lg shadow-blue-500/30 animate-pulse",
      dotClass: "bg-blue-300 animate-ping",
    };
  } else if (isInterviewerThinking) {
    stateBadge = {
      label: "Reasoning...",
      icon: Cpu,
      badgeClass: "bg-indigo-600/20 border-indigo-500/40 text-indigo-300 animate-pulse",
      dotClass: "bg-indigo-400 animate-ping",
    };
  } else if (isCandidateWorking) {
    stateBadge = {
      label: "Reviewing Code",
      icon: Pause,
      badgeClass: "bg-amber-500/15 border-amber-500/30 text-amber-300",
      dotClass: "bg-amber-400",
    };
  }

  return (
    <div className="relative flex flex-col justify-between p-4 rounded-2xl glass-panel border border-slate-800/90 bg-gradient-to-b from-slate-900/95 via-slate-900/90 to-slate-950/95 shadow-2xl overflow-hidden shrink-0 w-full aspect-[16/11]">
      {/* Dynamic Ambient Glow Field */}
      <div
        className="absolute inset-0 transition-opacity duration-300 pointer-events-none"
        style={{
          background: isSpeaking
            ? `radial-gradient(circle at center, rgba(59, 130, 246, 0.25) 0%, rgba(99, 102, 241, 0.12) 40%, transparent 75%)`
            : `radial-gradient(circle at center, rgba(30, 41, 59, 0.4) 0%, transparent 70%)`,
        }}
      />

      {/* Top Header: Interviewer identity & Stage */}
      <div className="w-full flex items-center justify-between z-10">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950/80 backdrop-blur-md border border-slate-800 text-[11px] text-slate-200 font-semibold shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>{name}</span>
          <span className="text-[10px] text-slate-400 font-normal">({targetCompany})</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-950/80 backdrop-blur-md border border-blue-800/50 text-[10px] text-blue-300 font-semibold uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-ping" />
          <span>{currentStage.replace(/_/g, " ")}</span>
        </div>
      </div>

      {/* Center: Lifelike Photorealistic Portrait with Audio Wave Halo */}
      <div className="relative my-auto flex flex-col items-center justify-center z-10 py-1">
        {/* Pulsing Aura Rings */}
        <div
          className="absolute rounded-full transition-all duration-200"
          style={{
            width: isSpeaking ? "130px" : "110px",
            height: isSpeaking ? "130px" : "110px",
            background: isSpeaking
              ? "radial-gradient(circle, rgba(59,130,246,0.4) 0%, rgba(99,102,241,0.15) 70%, transparent 100%)"
              : "radial-gradient(circle, rgba(148,163,184,0.1) 0%, transparent 70%)",
            filter: "blur(12px)",
            transform: isSpeaking ? `scale(${1 + frequencyLevel * 0.005})` : "scale(1)",
          }}
        />

        {/* Outer Circular Ring with Status Color */}
        <div
          className={`relative p-1 rounded-full transition-all duration-300 shadow-xl ${
            isSpeaking
              ? "ring-4 ring-blue-500/80 ring-offset-2 ring-offset-slate-950 shadow-blue-500/30"
              : isInterviewerThinking
              ? "ring-2 ring-indigo-500/70 ring-offset-2 ring-offset-slate-950"
              : "ring-2 ring-slate-700/60 ring-offset-2 ring-offset-slate-950"
          }`}
        >
          {/* Real Avatar Photo Tile */}
          <div className="relative w-24 h-24 sm:w-28 sm:h-28 rounded-full overflow-hidden bg-slate-950 border border-slate-700/80 shadow-inner">
            <Image
              src={avatarImage}
              alt={name}
              fill
              className={`object-cover object-top transition-transform duration-500 ${
                isSpeaking ? "scale-105" : "scale-100"
              }`}
              priority
            />

            {/* Subtle Overlay gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/40 via-transparent to-transparent pointer-events-none" />
          </div>
        </div>

        {/* Live Audio Spectrum Waveform Bar */}
        <div className="w-48 h-8 mt-2 relative flex items-center justify-center">
          <canvas
            ref={canvasRef}
            width={192}
            height={32}
            className="w-full h-full opacity-90"
          />
        </div>
      </div>

      {/* Bottom Bar: Title, Archetype & Active State Pill */}
      <div className="w-full flex items-center justify-between z-10 pt-2 border-t border-slate-800/60">
        <div className="flex flex-col">
          <span className="text-[11px] font-semibold text-slate-200">{title}</span>
          <span className="text-[9px] text-blue-400 font-medium">{archetype}</span>
        </div>

        {/* State Indicator Pill */}
        <div
          className={`px-3 py-1 rounded-full border text-[10px] font-bold flex items-center gap-1.5 transition-all ${stateBadge.badgeClass}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${stateBadge.dotClass}`} />
          <stateBadge.icon className="w-3 h-3" />
          <span>{stateBadge.label}</span>
        </div>
      </div>
    </div>
  );
}
