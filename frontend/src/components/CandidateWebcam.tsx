"use client";

import React, { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Mic, MicOff, Clock, ShieldCheck } from "lucide-react";

interface CandidateWebcamProps {
  onMuteToggle?: (isMuted: boolean) => void;
  isMicMuted?: boolean;
}

export default function CandidateWebcam({
  onMuteToggle,
  isMicMuted = false,
}: CandidateWebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [isCameraActive, setIsCameraActive] = useState(true);
  const [presenceSeconds, setPresenceSeconds] = useState(0);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  // Presence timer
  useEffect(() => {
    const timer = setInterval(() => {
      setPresenceSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Format presence timer mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Initialize local-only webcam stream
  useEffect(() => {
    let mounted = true;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
          audio: false, // Audio managed by audioStream.ts separately
        });

        if (mounted) {
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
          setHasPermission(true);
        }
      } catch (err) {
        console.warn("Camera access denied or unavailable:", err);
        if (mounted) {
          setHasPermission(false);
          setIsCameraActive(false);
        }
      }
    }

    if (isCameraActive) {
      setupCamera();
    } else {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    }

    return () => {
      mounted = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [isCameraActive]);

  const toggleCamera = () => {
    setIsCameraActive((prev) => !prev);
  };

  return (
    <div className="relative rounded-2xl overflow-hidden glass-panel border border-slate-800 bg-slate-900/90 shadow-2xl flex flex-col aspect-video w-full max-w-md mx-auto">
      {/* Top Overlay: Presence Timer and Privacy Badge */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-950/80 backdrop-blur-md border border-slate-800 text-[11px] text-slate-300 font-medium">
          <Clock className="w-3.5 h-3.5 text-blue-400" />
          <span>{formatTime(presenceSeconds)}</span>
        </div>

        <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-950/80 backdrop-blur-md border border-emerald-800/60 text-[10px] text-emerald-300 font-medium tracking-tight">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>100% Local (Zero Stream)</span>
        </div>
      </div>

      {/* Main Video Tile */}
      <div className="relative flex-1 bg-slate-950 flex items-center justify-center overflow-hidden">
        {isCameraActive && hasPermission ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover transform -scale-x-100" // Mirror self-view like Zoom
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-500 p-6 text-center">
            <CameraOff className="w-12 h-12 mb-2 text-slate-600" />
            <p className="text-xs font-medium">Camera is disabled</p>
            <p className="text-[10px] text-slate-600 mt-1">
              Desensitization self-view is turned off
            </p>
          </div>
        )}
      </div>

      {/* Bottom Controls Bar */}
      <div className="p-3 bg-slate-900/95 border-t border-slate-800 flex items-center justify-between z-20">
        <span className="text-xs font-medium text-slate-300 pl-1">You (Candidate)</span>

        <div className="flex items-center gap-2">
          {/* Microphone Mute Toggle */}
          <button
            type="button"
            onClick={() => onMuteToggle && onMuteToggle(!isMicMuted)}
            className={`p-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
              isMicMuted
                ? "bg-rose-600/20 text-rose-300 border border-rose-800/50 hover:bg-rose-600/30"
                : "bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700"
            }`}
            title={isMicMuted ? "Unmute Microphone" : "Mute Microphone"}
          >
            {isMicMuted ? <MicOff className="w-4 h-4 text-rose-400" /> : <Mic className="w-4 h-4 text-emerald-400" />}
          </button>

          {/* Camera Toggle */}
          <button
            type="button"
            onClick={toggleCamera}
            className={`p-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${
              !isCameraActive
                ? "bg-amber-600/20 text-amber-300 border border-amber-800/50 hover:bg-amber-600/30"
                : "bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700"
            }`}
            title={isCameraActive ? "Turn Off Camera" : "Turn On Camera"}
          >
            {isCameraActive ? <Camera className="w-4 h-4 text-blue-400" /> : <CameraOff className="w-4 h-4 text-amber-400" />}
          </button>
        </div>
      </div>
    </div>
  );
}
