"use client";

import React, { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Code,
  Cpu,
  FileQuestion,
  PhoneOff,
  ChevronRight,
  Sparkles,
  Shield,
  Volume2,
  Clock,
  Layers,
  Pause,
} from "lucide-react";
import InterviewerAvatar from "@/components/InterviewerAvatar";
import CandidateWebcam from "@/components/CandidateWebcam";
import CodeSandbox from "@/components/CodeSandbox";
import SystemDesignCanvas from "@/components/SystemDesignCanvas";
import { AudioPlayerQueue, AudioRecorder } from "@/lib/audioStream";

export default function InterviewRoomPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [activeTab, setActiveTab] = useState<"code" | "canvas" | "prompt">("code");
  const [sessionData, setSessionData] = useState<any>(null);
  const [activeQuestion, setActiveQuestion] = useState<any>(null);
  const [fsmSnapshot, setFsmSnapshot] = useState<any>(null);
  const [transcripts, setTranscripts] = useState<Array<{ speaker: string; text: string }>>([]);
  const [latestCaption, setLatestCaption] = useState<string>("");

  // Audio state
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [frequencyLevel, setFrequencyLevel] = useState(0);
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isCandidateWorking, setIsCandidateWorking] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  const audioPlayerRef = useRef<AudioPlayerQueue | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Load session details from backend
  useEffect(() => {
    async function fetchSession() {
      try {
        const res = await fetch(`http://localhost:8000/api/session/${sessionId}`);
        if (res.ok) {
          const data = await res.json();
          setSessionData(data);
          if (data.active_question) {
            setActiveQuestion(data.active_question);
          }
        }
      } catch (err) {
        console.error("Could not fetch session:", err);
      }
    }
    if (sessionId) {
      fetchSession();
    }
  }, [sessionId]);

  // Establish WebSocket connection and Audio streaming
  useEffect(() => {
    if (!sessionId) return;

    const apiKey = typeof window !== "undefined" ? sessionStorage.getItem("ai_interviewer_api_key") || "" : "";
    const wsUrl = `ws://localhost:8000/ws/interview/${sessionId}${apiKey ? `?api_key=${apiKey}` : ""}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    const audioPlayer = new AudioPlayerQueue(24000);
    audioPlayerRef.current = audioPlayer;

    // Visualizer loop reading frequency from AudioPlayerQueue
    const updateFrequency = () => {
      if (audioPlayerRef.current) {
        const freq = audioPlayerRef.current.getFrequencyData();
        setFrequencyLevel(freq);
        setIsSpeaking(freq > 5);
      }
      animFrameRef.current = requestAnimationFrame(updateFrequency);
    };
    animFrameRef.current = requestAnimationFrame(updateFrequency);

    // Audio Recorder (16kHz PCM capture)
    const audioRecorder = new AudioRecorder((base64Pcm) => {
      if (!isMicMuted && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "audio", data: base64Pcm }));
      }
    }, 16000);
    audioRecorderRef.current = audioRecorder;

    ws.onopen = async () => {
      console.log("WebSocket connected to interview multiplexer");
      try {
        await audioRecorder.start();
      } catch (e) {
        console.warn("Microphone access pending or denied:", e);
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "fsm_snapshot") {
          setFsmSnapshot(msg.data);
          if (msg.data.active_question) {
            setActiveQuestion(msg.data.active_question);
          }
        } else if (msg.type === "transcript_caption") {
          setLatestCaption(msg.text);
          setTranscripts((prev) => [...prev, { speaker: msg.speaker, text: msg.text }]);
        } else if (msg.type === "audio_chunk") {
          audioPlayer.playChunk(msg.data);
        }
      } catch (err) {
        console.error("Error processing ws message:", err);
      }
    };

    return () => {
      ws.close();
      audioRecorder.stop();
      audioPlayer.stop();
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [sessionId, isMicMuted]);

  // Keystroke VAD Gate: notify backend when candidate is actively typing/drawing
  const handleWorkingStateChange = (isActive: boolean) => {
    setIsCandidateWorking(isActive);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "working_state",
          is_active: isActive,
        })
      );
    }
  };

  const handleCodeExecuted = (payload: { language: string; code: string; stdout: string; error?: string }) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "code_update",
          language: payload.language,
          code: payload.code,
          stdout: payload.stdout,
          error: payload.error,
        })
      );
    }
  };

  const handleCanvasSnapshot = (dataUrl: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "canvas_update",
          image_base64: dataUrl,
        })
      );
    }
  };

  const handleAdvanceStage = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/session/${sessionId}/advance_stage`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setFsmSnapshot((prev: any) => ({
          ...prev,
          current_stage: data.new_stage,
        }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleEndInterview = () => {
    router.push(`/report/${sessionId}`);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden select-none">
      {/* Stage & Timer Header Bar */}
      <header className="h-14 px-6 bg-slate-950/95 border-b border-slate-800/80 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-sm text-slate-200">
              {sessionData?.target_company} — {sessionData?.target_role}
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          {/* FSM Stage Badge */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-slate-300 font-medium">
              Stage {fsmSnapshot?.stage_index || 1}/{fsmSnapshot?.total_stages || 5}:{" "}
              <strong className="text-white">
                {(fsmSnapshot?.current_stage || "INTRO").replace(/_/g, " ")}
              </strong>
            </span>
          </div>

          {/* Typing / Thinking Hold Indicator */}
          {isCandidateWorking && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs animate-pulse">
              <Pause className="w-3 h-3" />
              <span>Thinking / Typing Hold Active</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleAdvanceStage}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 border border-slate-700 transition-colors"
          >
            Advance Stage <ChevronRight className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={handleEndInterview}
            className="px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-rose-600/20 transition-colors"
          >
            <PhoneOff className="w-3.5 h-3.5" /> End Call & Get Scorecard
          </button>
        </div>
      </header>

      {/* Main Dual-Pane Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane (40% width - The Interview Room) */}
        <div className="w-[40%] border-r border-slate-800/80 bg-slate-950 flex flex-col p-4 gap-4 overflow-y-auto">
          {/* AI Interviewer Avatar Tile */}
          <InterviewerAvatar
            isSpeaking={isSpeaking}
            frequencyLevel={frequencyLevel}
            currentStage={fsmSnapshot?.current_stage || "INTRO"}
          />

          {/* Candidate Webcam Tile */}
          <CandidateWebcam
            isMicMuted={isMicMuted}
            onMuteToggle={(muted) => setIsMicMuted(muted)}
          />

          {/* Live Transcript / Closed Caption Box */}
          <div className="flex-1 min-h-[140px] rounded-2xl glass-panel border border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                Live Subtitles & Probing Stream
              </span>
              <p className="text-xs text-slate-200 leading-relaxed italic">
                {latestCaption ? `"${latestCaption}"` : "Listening to room audio..."}
              </p>
            </div>
            <div className="text-[10px] text-slate-500 pt-2 border-t border-slate-800/60 flex items-center justify-between">
              <span>Dual-Loop Active: Gemini Live (Fast) + Shadow Supervisor (Slow)</span>
              <span className="text-emerald-400">Connected</span>
            </div>
          </div>
        </div>

        {/* Right Pane (60% width - Interactive Technical Workbench) */}
        <div className="w-[60%] bg-slate-950 flex flex-col overflow-hidden">
          {/* Workbench Tabs Header */}
          <div className="h-11 px-4 bg-slate-900/70 border-b border-slate-800/80 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveTab("code")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                  activeTab === "code"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Code className="w-3.5 h-3.5" /> Live Coding (Monaco + WASM)
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("canvas")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                  activeTab === "canvas"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Cpu className="w-3.5 h-3.5" /> ML System Design Canvas
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("prompt")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                  activeTab === "prompt"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <FileQuestion className="w-3.5 h-3.5" /> Problem Prompt
              </button>
            </div>
          </div>

          {/* Workbench Tab Content */}
          <div className="flex-1 p-4 overflow-hidden">
            {activeTab === "code" && (
              <CodeSandbox
                initialLanguage={activeQuestion?.category === "SQL" ? "sql" : "python"}
                initialCode={activeQuestion?.starter_code || "# Write your Python solution here\n"}
                seedSql={activeQuestion?.seed_sql}
                unitTests={activeQuestion?.unit_tests}
                onCodeExecuted={handleCodeExecuted}
                onWorkingStateChange={handleWorkingStateChange}
              />
            )}

            {activeTab === "canvas" && (
              <SystemDesignCanvas
                onSnapshot={handleCanvasSnapshot}
                onWorkingStateChange={handleWorkingStateChange}
              />
            )}

            {activeTab === "prompt" && (
              <div className="h-full rounded-2xl glass-panel border border-slate-800 bg-slate-900/95 p-6 overflow-y-auto space-y-6">
                <div>
                  <span className="inline-block px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-2">
                    {activeQuestion?.category || "Problem Statement"}
                  </span>
                  <h2 className="text-xl font-bold text-white">
                    {activeQuestion?.title || "Live Interview Technical Problem"}
                  </h2>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {activeQuestion?.prompt || "No active problem selected for this stage."}
                  </p>
                </div>

                {activeQuestion?.rubric_criteria && (
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                      Bar-Raiser Rubric Evaluation Focus
                    </h3>
                    <ul className="space-y-2">
                      {activeQuestion.rubric_criteria.map((c: string, idx: number) => (
                        <li
                          key={idx}
                          className="text-xs text-slate-300 flex items-start gap-2 bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/60"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
