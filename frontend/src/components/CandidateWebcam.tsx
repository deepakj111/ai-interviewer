"use client";

import React, { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, Mic, MicOff, Clock, ShieldCheck } from "lucide-react";

interface CandidateWebcamProps {
  onMuteToggle?: (isMuted: boolean) => void;
  isMicMuted?: boolean;
  startTime?: string | number | null;
}

export default function CandidateWebcam({
  onMuteToggle,
  isMicMuted = false,
  startTime = null,
}: CandidateWebcamProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [isCameraActive, setIsCameraActive] = useState(true);
  const [presenceSeconds, setPresenceSeconds] = useState(0);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  // Persistent presence timer derived from session start timestamp
  useEffect(() => {
    const updateElapsed = () => {
      if (startTime) {
        const startMs = typeof startTime === "number" ? startTime : new Date(startTime).getTime();
        const diff = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
        setPresenceSeconds(diff);
      } else {
        setPresenceSeconds((prev) => prev + 1);
      }
    };

    updateElapsed();
    const timer = setInterval(updateElapsed, 1000);
    return () => clearInterval(timer);
  }, [startTime]);

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
            videoRef.current.play().catch((e) => console.warn("Video play error:", e));
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

  // Ensure stream stays bound to video ref when permissions or state update
  useEffect(() => {
    if (videoRef.current && streamRef.current && isCameraActive && hasPermission) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch((err) => {
        console.warn("Webcam play promise catch:", err);
      });
    }
  }, [hasPermission, isCameraActive]);

  const toggleCamera = () => {
    setIsCameraActive((prev) => !prev);
  };

  return (
    <div className="relative rounded-2xl overflow-hidden glass-panel border border-slate-800 bg-slate-900/90 shadow-2xl flex flex-col aspect-video w-full max-w-md mx-auto shrink-0">
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

      {/* Main Video Tile - Video kept in DOM so srcObject attaches reliably */}
      <div className="relative flex-1 bg-slate-950 flex items-center justify-center overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          onLoadedMetadata={() => {
            videoRef.current?.play().catch(() => {});
          }}
          className={`w-full h-full object-cover transform -scale-x-100 ${
            isCameraActive && hasPermission ? "block" : "hidden"
          }`}
        />

        {(!isCameraActive || !hasPermission) && (
          <div className="flex flex-col items-center justify-center text-slate-500 p-6 text-center">
            <CameraOff className="w-10 h-10 mb-2 text-slate-600" />
            <p className="text-xs font-medium">Camera is disabled</p>
            <p className="text-[10px] text-slate-600 mt-1">
              {hasPermission === false
                ? "Camera permission denied or camera in use by another application."
                : "Desensitization self-view is turned off"}
            </p>
          </div>
        )}
      </div>

      {/* Bottom Controls Bar */}
      <div className="p-2.5 bg-slate-900/95 border-t border-slate-800 flex items-center justify-between z-20">
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
            {isMicMuted ? <MicOff className="w-3.5 h-3.5 text-rose-400" /> : <Mic className="w-3.5 h-3.5 text-emerald-400" />}
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
            {isCameraActive ? <Camera className="w-3.5 h-3.5 text-blue-400" /> : <CameraOff className="w-3.5 h-3.5 text-amber-400" />}
          </button>
        </div>
      </div>
    </div>
  );
}
