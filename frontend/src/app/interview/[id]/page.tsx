"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Code,
  Cpu,
  FileQuestion,
  PhoneOff,
  ChevronRight,
  Sparkles,
  Volume2,
  VolumeX,
  Clock,
  Layers,
  Pause,
  Send,
  Radio,
  UserCheck,
  Shuffle,
  Hand,
  Globe,
  Building2,
  Rocket,
  HelpCircle,
  Lightbulb,
  Headphones,
  Mic,
  MicOff,
  X,
  Sliders,
  CheckCircle2,
} from "lucide-react";
import InterviewerAvatar from "@/components/InterviewerAvatar";
import CandidateWebcam from "@/components/CandidateWebcam";
import CodeSandbox from "@/components/CodeSandbox";
import SystemDesignCanvas from "@/components/SystemDesignCanvas";
import { AudioPlayerQueue, AudioRecorder } from "@/lib/audioStream";
import { INTERVIEWER_PERSONAS, InterviewerPersona, voiceManager } from "@/lib/voiceManager";
import { getApiUrl, getWsUrl } from "@/lib/api";

function getStagesPipeline(interviewMode?: string) {
  switch (interviewMode) {
    case "ML_BREADTH":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "ML_BREADTH", label: "ML Breadth Sprint" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "ML_DEPTH":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "ML_DEPTH", label: "Deep-Dive Theory" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "GENERATIVE_AI_LLM":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "GENERATIVE_AI", label: "GenAI & LLM Architecture" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "SQL_PYTHON_CODING":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "LIVE_CODING_SQL_PYTHON", label: "Coding Sprint" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "ML_SYSTEM_DESIGN":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "ML_SYSTEM_DESIGN", label: "System Architecture" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "RESUME_DEEP_DIVE":
      return [
        { id: "INTRO", label: "Intro" },
        { id: "RESUME_DEEP_DIVE", label: "Project Deep-Dive" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
    case "FULL_LOOP":
    default:
      return [
        { id: "INTRO", label: "Intro" },
        { id: "RESUME_DEEP_DIVE", label: "Resume" },
        { id: "LIVE_CODING_SQL_PYTHON", label: "Coding" },
        { id: "ML_SYSTEM_DESIGN", label: "Design" },
        { id: "BEHAVIORAL_BAR_RAISER", label: "Wrap-up" },
      ];
  }
}

export default function InterviewRoomPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [activeTab, setActiveTab] = useState<"code" | "canvas" | "prompt">("code");
  const [sessionData, setSessionData] = useState<any>(null);
  const [activeQuestion, setActiveQuestion] = useState<any>(null);
  const [fsmSnapshot, setFsmSnapshot] = useState<any>(null);
  const [transcripts, setTranscripts] = useState<Array<{ speaker: string; text: string; time?: string }>>([]);
  const [latestCaption, setLatestCaption] = useState<string>("");
  const [candidateInputText, setCandidateInputText] = useState("");

  // Persona & Voice State
  const [selectedPersona, setSelectedPersona] = useState<InterviewerPersona>(voiceManager.getPersona());
  const [isTestingVoice, setIsTestingVoice] = useState(false);

  // Persistent Timer
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Audio state & Echo Prevention Refs
  const [isSpeaking, setIsSpeaking] = useState(false);
  const isSpeakingRef = useRef(false);
  const lastSpokeTimestampRef = useRef<number>(0);
  const lastCandidateActivityRef = useRef<number>(Date.now());
  const [silencePrompt, setSilencePrompt] = useState<string | null>(null);

  const [frequencyLevel, setFrequencyLevel] = useState(0);
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isTtsEnabled, setIsTtsEnabled] = useState(true);
  const [isCandidateWorking, setIsCandidateWorking] = useState(false);
  const [isInterviewerThinking, setIsInterviewerThinking] = useState(false);

  // 2026 Turn-Taking Voice Control Modes
  // 'handsfree' = automatic VAD with 3.5s thinking pause
  // 'push_to_talk' = hold spacebar or mic button to talk, release to send
  const [voiceInputMode, setVoiceInputMode] = useState<"handsfree" | "push_to_talk">("handsfree");
  const [isPushToTalkActive, setIsPushToTalkActive] = useState(false);
  const [pauseCountdown, setPauseCountdown] = useState<number | null>(null);

  // Speech Recognition & Turn Dispatching State
  const [liveSpeechPreview, setLiveSpeechPreview] = useState<string>("");
  const [isLiveListening, setIsLiveListening] = useState<boolean>(false);
  const speechBufferRef = useRef<string>("");
  const speechSendTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMicMutedRef = useRef(false);
  const isMountedRef = useRef(true);
  const interviewerSpokeStartTimeRef = useRef<number>(0);
  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  const audioPlayerRef = useRef<AudioPlayerQueue | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const hasLiveAudioRef = useRef(false);
  const speechRecRef = useRef<any>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript feed
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, isInterviewerThinking]);

  // Load session details from API
  useEffect(() => {
    async function fetchSession() {
      try {
        const res = await fetch(getApiUrl(`/api/session/${sessionId}`));
        if (res.ok) {
          const data = await res.json();
          setSessionData(data);
          if (data.active_question) {
            setActiveQuestion(data.active_question);
          }

          const storageKey = `session_start_${sessionId}`;
          let startMs = 0;
          if (typeof window !== "undefined") {
            const cached = localStorage.getItem(storageKey);
            if (cached) {
              startMs = parseInt(cached, 10);
            } else if (data.created_at) {
              startMs = new Date(data.created_at).getTime();
              localStorage.setItem(storageKey, startMs.toString());
            }
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

  // Persistent Timer Interval
  useEffect(() => {
    const updateTimer = () => {
      const storageKey = `session_start_${sessionId}`;
      if (typeof window !== "undefined") {
        let startMs = 0;
        const cached = localStorage.getItem(storageKey);
        if (cached) {
          startMs = parseInt(cached, 10);
        } else if (sessionData?.created_at) {
          startMs = new Date(sessionData.created_at).getTime();
          localStorage.setItem(storageKey, startMs.toString());
        }

        if (startMs > 0) {
          const diff = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
          setElapsedSeconds(diff);
        }
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [sessionId, sessionData]);

  // Proactive Human-Like Silence Monitor
  useEffect(() => {
    let lastPingStage = 0;

    const silenceCheck = setInterval(() => {
      const idleSec = Math.floor((Date.now() - lastCandidateActivityRef.current) / 1000);

      if (idleSec >= 20 && speechBufferRef.current.length > 0) {
        speechBufferRef.current = "";
        setLiveSpeechPreview("");
      }

      if (isSpeakingRef.current || isCandidateWorking || speechBufferRef.current.length > 0 || isPushToTalkActive) {
        lastPingStage = 0;
        return;
      }

      // 35s of quiet
      if (idleSec >= 35 && idleSec < 75 && lastPingStage < 1) {
        lastPingStage = 1;
        setSilencePrompt("Take your time. Feel free to think out loud or ask for constraints.");
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          setIsInterviewerThinking(true);
          socketRef.current.send(JSON.stringify({ type: "silence_ping", seconds_silent: 35 }));
        }
      } else if (idleSec >= 75 && idleSec < 120 && lastPingStage < 2) {
        lastPingStage = 2;
        setSilencePrompt("Need a hint or want to discuss trade-offs? Click 'Get Hint' or ask directly.");
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          setIsInterviewerThinking(true);
          socketRef.current.send(JSON.stringify({ type: "silence_ping", seconds_silent: 75 }));
        }
      } else if (idleSec >= 120 && lastPingStage < 3) {
        lastPingStage = 3;
        setSilencePrompt("Would you like to review the starter requirements together?");
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          setIsInterviewerThinking(true);
          socketRef.current.send(JSON.stringify({ type: "silence_ping", seconds_silent: 120 }));
        }
      }
    }, 4000);

    return () => clearInterval(silenceCheck);
  }, [isCandidateWorking, isPushToTalkActive]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Instant Barge-In / Interruption Handler
  const handleInterrupt = useCallback(() => {
    voiceManager.cancel();
    if (audioPlayerRef.current) {
      audioPlayerRef.current.stop();
    }
    isSpeakingRef.current = false;
    setIsSpeaking(false);
    setFrequencyLevel(0);
    lastSpokeTimestampRef.current = Date.now();
    lastCandidateActivityRef.current = Date.now();
    setSilencePrompt(null);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "interrupt" }));
    }
  }, []);

  // Centralized Candidate Turn Dispatcher
  const dispatchCandidateTurn = useCallback(
    (rawText: string) => {
      const text = rawText.trim();
      if (!text) return;

      if (isSpeakingRef.current) {
        handleInterrupt();
      }

      lastCandidateActivityRef.current = Date.now();
      setSilencePrompt(null);
      setLiveSpeechPreview("");
      speechBufferRef.current = "";
      setPauseCountdown(null);

      if (speechSendTimeoutRef.current) {
        clearTimeout(speechSendTimeoutRef.current);
        speechSendTimeoutRef.current = null;
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
      }

      if (speechRecRef.current) {
        try {
          speechRecRef.current.abort();
        } catch (_) {}
      }

      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        setIsInterviewerThinking(true);
        if (thinkingTimeoutRef.current) {
          clearTimeout(thinkingTimeoutRef.current);
        }
        thinkingTimeoutRef.current = setTimeout(() => {
          setIsInterviewerThinking(false);
        }, 12000);

        socketRef.current.send(
          JSON.stringify({
            type: "text_turn",
            text: text,
          })
        );
        const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setTranscripts((prev) => [...prev, { speaker: "candidate", text: text, time: timeStr }]);
      }
    },
    [handleInterrupt]
  );

  // Push-to-Talk and Spacebar Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable ||
          target.closest(".monaco-editor"));

      if (isInput) return;

      // Spacebar to cut-in if speaking
      if (e.code === "Space" && isSpeakingRef.current) {
        e.preventDefault();
        handleInterrupt();
        return;
      }

      // Spacebar for push-to-talk mode
      if (e.code === "Space" && voiceInputMode === "push_to_talk" && !isPushToTalkActive) {
        e.preventDefault();
        setIsPushToTalkActive(true);
        setIsMicMuted(false);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space" && voiceInputMode === "push_to_talk" && isPushToTalkActive) {
        e.preventDefault();
        setIsPushToTalkActive(false);
        // Flush speech buffer immediately on release
        if (speechBufferRef.current.trim().length > 0) {
          dispatchCandidateTurn(speechBufferRef.current.trim());
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [handleInterrupt, voiceInputMode, isPushToTalkActive, dispatchCandidateTurn]);

  // Speech Synthesis with Persona-Locked Voice
  const speakInterviewerCaption = useCallback(
    (text: string) => {
      if (!isTtsEnabled) return;
      if (hasLiveAudioRef.current) return;

      interviewerSpokeStartTimeRef.current = Date.now();
      isSpeakingRef.current = true;
      setIsSpeaking(true);

      voiceManager.speak(text, {
        onStart: () => {
          interviewerSpokeStartTimeRef.current = Date.now();
          isSpeakingRef.current = true;
          setIsSpeaking(true);
        },
        onEnd: () => {
          isSpeakingRef.current = false;
          setIsSpeaking(false);
          lastSpokeTimestampRef.current = Date.now();
          lastCandidateActivityRef.current = Date.now();
          setFrequencyLevel(0);
        },
        onFrequency: (freq) => {
          setFrequencyLevel(freq);
        },
      });
    },
    [isTtsEnabled]
  );

  const handlePersonaChange = (personaId: string) => {
    voiceManager.setPersona(personaId);
    const newPersona = voiceManager.getPersona();
    setSelectedPersona(newPersona);
  };

  const handleTestVoice = () => {
    if (isTestingVoice) return;
    setIsTestingVoice(true);
    isSpeakingRef.current = true;
    setIsSpeaking(true);
    voiceManager.speak(
      `Hello! I am ${selectedPersona.name}. I'm excited to collaborate with you on today's technical problems.`,
      {
        onStart: () => {
          isSpeakingRef.current = true;
          setIsSpeaking(true);
        },
        onEnd: () => {
          isSpeakingRef.current = false;
          setIsSpeaking(false);
          setIsTestingVoice(false);
          lastSpokeTimestampRef.current = Date.now();
          setFrequencyLevel(0);
        },
        onFrequency: (freq) => setFrequencyLevel(freq),
      }
    );
  };

  const stagesPipeline = getStagesPipeline(sessionData?.interview_mode);

  useEffect(() => {
    isMicMutedRef.current = isMicMuted;
  }, [isMicMuted]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Web SpeechRecognition with Generous 3.5s Thinking Pause and PTT support
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("SpeechRecognition API not available in this browser");
      return;
    }

    if (isMicMuted && !(voiceInputMode === "push_to_talk" && isPushToTalkActive)) {
      if (speechRecRef.current) {
        try {
          speechRecRef.current.stop();
        } catch (_) {}
      }
      setIsLiveListening(false);
      return;
    }

    let isEffectActive = true;

    const startRecognition = () => {
      if (!isEffectActive || !isMountedRef.current || isMicMutedRef.current) {
        return;
      }

      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onstart = () => {
          if (isEffectActive) setIsLiveListening(true);
        };

        recognition.onspeechstart = () => {
          lastCandidateActivityRef.current = Date.now();
          setSilencePrompt(null);
          setPauseCountdown(null);
          if (speechSendTimeoutRef.current) {
            clearTimeout(speechSendTimeoutRef.current);
            speechSendTimeoutRef.current = null;
          }
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
            countdownIntervalRef.current = null;
          }
        };

        recognition.onresult = (event: any) => {
          // If interviewer is speaking and candidate speaks substantively, cut in immediately!
          if (isSpeakingRef.current) {
            let bargeText = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
              bargeText += event.results[i][0].transcript + " ";
            }
            if (bargeText.trim().length > 3) {
              handleInterrupt();
            }
            return;
          }

          // Ignore acoustic echo right after interviewer stops
          if (Date.now() - lastSpokeTimestampRef.current < 600) {
            return;
          }

          lastCandidateActivityRef.current = Date.now();
          setSilencePrompt(null);

          let fullTranscript = "";
          for (let i = 0; i < event.results.length; i++) {
            fullTranscript += event.results[i][0].transcript + " ";
          }
          const cleanTranscript = fullTranscript.trim();

          if (cleanTranscript.length > 0) {
            speechBufferRef.current = cleanTranscript;
            setLiveSpeechPreview(cleanTranscript);

            // In Push-to-Talk mode, do not auto-send until user releases key/button
            if (voiceInputMode === "push_to_talk") {
              return;
            }

            // In Hands-free mode, give candidate a generous 3.5s pause to think and speak
            if (speechSendTimeoutRef.current) {
              clearTimeout(speechSendTimeoutRef.current);
            }
            if (countdownIntervalRef.current) {
              clearInterval(countdownIntervalRef.current);
            }

            let remainingSec = 3.5;
            setPauseCountdown(remainingSec);

            countdownIntervalRef.current = setInterval(() => {
              remainingSec = Math.max(0, Math.round((remainingSec - 0.5) * 10) / 10);
              setPauseCountdown(remainingSec);
              if (remainingSec <= 0 && countdownIntervalRef.current) {
                clearInterval(countdownIntervalRef.current);
                countdownIntervalRef.current = null;
              }
            }, 500);

            speechSendTimeoutRef.current = setTimeout(() => {
              if (speechBufferRef.current.trim().length > 0) {
                dispatchCandidateTurn(speechBufferRef.current.trim());
              }
            }, 3500);
          }
        };

        recognition.onerror = (e: any) => {
          if (e.error !== "no-speech") {
            console.warn("Speech recognition notice:", e.error);
          }
          if (e.error === "not-allowed") {
            setIsMicMuted(true);
            setIsLiveListening(false);
          }
        };

        recognition.onend = () => {
          if (isEffectActive) setIsLiveListening(false);

          // In hands-free mode, if buffer exists and no timeout running, send
          if (
            voiceInputMode === "handsfree" &&
            speechBufferRef.current.trim().length > 0 &&
            !speechSendTimeoutRef.current
          ) {
            dispatchCandidateTurn(speechBufferRef.current.trim());
          }

          // Keep microphone connection alive seamlessly
          if (isEffectActive && isMountedRef.current && !isMicMutedRef.current) {
            setTimeout(() => {
              if (isEffectActive && isMountedRef.current && !isMicMutedRef.current) {
                startRecognition();
              }
            }, 250);
          }
        };

        recognition.start();
        speechRecRef.current = recognition;
      } catch (err) {
        if (isEffectActive && isMountedRef.current && !isMicMutedRef.current) {
          setTimeout(startRecognition, 1000);
        }
      }
    };

    startRecognition();

    return () => {
      isEffectActive = false;
      if (speechSendTimeoutRef.current) {
        clearTimeout(speechSendTimeoutRef.current);
        speechSendTimeoutRef.current = null;
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
        countdownIntervalRef.current = null;
      }
      if (speechRecRef.current) {
        try {
          speechRecRef.current.stop();
        } catch (_) {}
      }
      setIsLiveListening(false);
    };
  }, [isMicMuted, handleInterrupt, dispatchCandidateTurn, voiceInputMode, isPushToTalkActive]);

  // Establish WebSocket connection and Audio streaming
  useEffect(() => {
    if (!sessionId) return;

    const apiKey = typeof window !== "undefined" ? sessionStorage.getItem("ai_interviewer_api_key") || "" : "";
    const wsUrl = getWsUrl(`/ws/interview/${sessionId}${apiKey ? `?api_key=${apiKey}` : ""}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    const audioPlayer = new AudioPlayerQueue(24000);
    audioPlayerRef.current = audioPlayer;

    const updateFrequency = () => {
      if (audioPlayerRef.current && hasLiveAudioRef.current) {
        const freq = audioPlayerRef.current.getFrequencyData();
        setFrequencyLevel(freq);
        setIsSpeaking(freq > 5);
        isSpeakingRef.current = freq > 5;
        if (freq > 5) {
          lastSpokeTimestampRef.current = Date.now();
        }
      }
      animFrameRef.current = requestAnimationFrame(updateFrequency);
    };
    animFrameRef.current = requestAnimationFrame(updateFrequency);

    const audioRecorder = new AudioRecorder((base64Pcm) => {
      if (!isMicMuted && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "audio", data: base64Pcm }));
      }
    }, 16000);
    audioRecorderRef.current = audioRecorder;

    ws.onopen = async () => {
      try {
        await audioRecorder.start();
      } catch (e) {
        console.warn("Microphone access pending:", e);
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
          if (msg.data.current_stage === "LIVE_CODING_SQL_PYTHON") {
            setActiveTab("code");
          } else if (msg.data.current_stage === "ML_SYSTEM_DESIGN") {
            setActiveTab("canvas");
          } else if (["ML_BREADTH", "ML_DEPTH", "GENERATIVE_AI", "BEHAVIORAL_BAR_RAISER"].includes(msg.data.current_stage)) {
            setActiveTab("prompt");
          }
        } else if (msg.type === "transcript_caption") {
          if (thinkingTimeoutRef.current) {
            clearTimeout(thinkingTimeoutRef.current);
            thinkingTimeoutRef.current = null;
          }
          setIsInterviewerThinking(false);
          setLatestCaption(msg.text);
          const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          setTranscripts((prev) => [...prev, { speaker: msg.speaker, text: msg.text, time: timeStr }]);
          if (msg.speaker === "interviewer") {
            speakInterviewerCaption(msg.text);
          }
        } else if (msg.type === "interrupted") {
          voiceManager.cancel();
          audioPlayer.stop();
          isSpeakingRef.current = false;
          setIsSpeaking(false);
          setFrequencyLevel(0);
        } else if (msg.type === "audio_chunk") {
          hasLiveAudioRef.current = true;
          isSpeakingRef.current = true;
          setIsSpeaking(true);
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
      voiceManager.cancel();
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [sessionId, isMicMuted, speakInterviewerCaption]);

  const handleSendCandidateText = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const text = candidateInputText.trim();
    if (!text) return;
    setCandidateInputText("");
    dispatchCandidateTurn(text);
  };

  const handleSendDirectPrompt = (prompt: string) => {
    if (!prompt.trim()) return;
    dispatchCandidateTurn(prompt);
  };

  const handleWorkingStateChange = (isActive: boolean) => {
    setIsCandidateWorking(isActive);
    if (isActive) {
      lastCandidateActivityRef.current = Date.now();
      setSilencePrompt(null);
    }
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
    lastCandidateActivityRef.current = Date.now();
    setSilencePrompt(null);
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setIsInterviewerThinking(true);
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
    lastCandidateActivityRef.current = Date.now();
    setSilencePrompt(null);
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
      const res = await fetch(getApiUrl(`/api/session/${sessionId}/advance_stage`), {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setFsmSnapshot((prev: any) => ({
          ...prev,
          current_stage: data.new_stage,
        }));
        if (data.new_stage === "LIVE_CODING_SQL_PYTHON") {
          setActiveTab("code");
        } else if (data.new_stage === "ML_SYSTEM_DESIGN") {
          setActiveTab("canvas");
        } else if (["ML_BREADTH", "ML_DEPTH", "GENERATIVE_AI", "BEHAVIORAL_BAR_RAISER"].includes(data.new_stage)) {
          setActiveTab("prompt");
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const [isSwitchingQuestion, setIsSwitchingQuestion] = useState(false);

  const handleSwitchQuestion = async () => {
    if (isSwitchingQuestion) return;
    setIsSwitchingQuestion(true);
    try {
      const res = await fetch(getApiUrl(`/api/session/${sessionId}/switch_question`), {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setActiveQuestion(data.new_question);
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          socketRef.current.send(
            JSON.stringify({
              type: "text_turn",
              text: `I'd like to work on '${data.new_question.title}'. Can you explain the problem and requirements?`,
            })
          );
        }
      }
    } catch (err) {
      console.error("Could not switch question:", err);
    } finally {
      setIsSwitchingQuestion(false);
    }
  };

  const handleEndInterview = () => {
    voiceManager.cancel();
    router.push(`/report/${sessionId}`);
  };

  const currentStageName = fsmSnapshot?.current_stage || "INTRO";
  const currentStageIdx = stagesPipeline.findIndex((s) => s.id === currentStageName);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden select-none">
      {/* Stage & Timer Header Bar */}
      <header className="h-14 px-5 bg-slate-950/95 border-b border-slate-800/80 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-sm text-slate-200">
              {sessionData?.target_company} — {sessionData?.target_role}
            </span>
          </div>

          {/* Company Archetype Badge */}
          {sessionData?.company_archetype === "INDIAN_PRODUCT" && (
            <span className="hidden sm:flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-300 text-[11px] font-semibold">
              🇮🇳 Indian Product Tech
            </span>
          )}
          {sessionData?.company_archetype === "AI_STARTUP" && (
            <span className="hidden sm:flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-[11px] font-semibold">
              <Rocket className="w-3 h-3 text-purple-400" />
              <span>AI Startup</span>
            </span>
          )}
          {sessionData?.company_archetype === "FAANG_GLOBAL" && (
            <span className="hidden sm:flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-[11px] font-semibold">
              <Building2 className="w-3 h-3 text-blue-400" />
              <span>Global Tech</span>
            </span>
          )}

          <div className="h-4 w-px bg-slate-800" />

          {/* Persistent Session Timer Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-200">
            <Clock className="w-3.5 h-3.5 text-blue-400" />
            <span>{formatTime(elapsedSeconds)}</span>
          </div>

          {/* Dynamic Visual Stage Stepper Pipeline */}
          <div className="hidden lg:flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px]">
            {stagesPipeline.map((stage, idx) => {
              const isPast = idx < currentStageIdx;
              const isCurrent = idx === currentStageIdx;
              return (
                <div key={stage.id} className="flex items-center gap-1">
                  <span
                    className={`px-2 py-0.5 rounded-full font-medium transition-colors ${
                      isCurrent
                        ? "bg-blue-600 text-white font-bold shadow-sm"
                        : isPast
                        ? "text-emerald-400"
                        : "text-slate-500"
                    }`}
                  >
                    {stage.label}
                  </span>
                  {idx < stagesPipeline.length - 1 && (
                    <span className="text-slate-700 text-[9px] font-bold">›</span>
                  )}
                </div>
              );
            })}
          </div>

          {isCandidateWorking && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs animate-pulse">
              <Pause className="w-3 h-3" />
              <span>Thinking / Typing Hold</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Barge-In / Cut-In Button */}
          {isSpeaking && (
            <button
              type="button"
              onClick={handleInterrupt}
              className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-amber-500/20 animate-pulse transition-all"
              title="Interrupt interviewer immediately (barge-in)"
            >
              <Hand className="w-3.5 h-3.5" />
              <span>Cut In / Speak</span>
            </button>
          )}

          {/* Persona Selector Dropdown */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl px-2.5 py-1 text-xs">
            <UserCheck className="w-3.5 h-3.5 text-blue-400 mr-1.5" />
            <select
              value={selectedPersona.id}
              onChange={(e) => handlePersonaChange(e.target.value)}
              className="bg-transparent text-slate-200 text-xs outline-none cursor-pointer pr-1"
            >
              {INTERVIEWER_PERSONAS.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                  {p.name} ({p.gender})
                </option>
              ))}
            </select>
          </div>

          {/* Test Voice Button */}
          <button
            type="button"
            onClick={handleTestVoice}
            disabled={isTestingVoice}
            className="px-2.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 text-xs font-medium flex items-center gap-1.5 transition-colors"
            title="Preview interviewer voice"
          >
            <Radio className={`w-3.5 h-3.5 text-blue-400 ${isTestingVoice ? "animate-spin" : ""}`} />
            <span>{isTestingVoice ? "Testing..." : "Test Voice"}</span>
          </button>

          {/* Turn-Taking Input Mode Switcher (Hands-free vs Push-to-Talk) */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setVoiceInputMode("handsfree")}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                voiceInputMode === "handsfree"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Hands-free conversational mode: AI listens with 3.5s thinking pause tolerance"
            >
              Hands-Free
            </button>
            <button
              type="button"
              onClick={() => setVoiceInputMode("push_to_talk")}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                voiceInputMode === "push_to_talk"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Push-to-Talk mode: Hold Spacebar or Mic to speak, release to send (zero premature cutoffs)"
            >
              Push-to-Talk
            </button>
          </div>

          {/* TTS Audio Voice Toggle */}
          <button
            type="button"
            onClick={() => {
              const next = !isTtsEnabled;
              setIsTtsEnabled(next);
              if (!next) {
                voiceManager.cancel();
              } else if (next && latestCaption) {
                speakInterviewerCaption(latestCaption);
              }
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 border transition-colors ${
              isTtsEnabled
                ? "bg-slate-900 border-slate-700 text-blue-300 hover:bg-slate-800"
                : "bg-slate-900/60 border-slate-800 text-slate-500 hover:text-slate-300"
            }`}
            title="Toggle Interviewer Voice Audio"
          >
            {isTtsEnabled ? <Volume2 className="w-3.5 h-3.5 text-blue-400" /> : <VolumeX className="w-3.5 h-3.5" />}
            <span>Voice {isTtsEnabled ? "On" : "Muted"}</span>
          </button>

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
            <PhoneOff className="w-3.5 h-3.5" /> End Call & Scorecard
          </button>
        </div>
      </header>

      {/* Main Dual-Pane Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane (38% width - The Interview Room) */}
        <div className="w-[38%] border-r border-slate-800/80 bg-slate-950 flex flex-col p-3 gap-3 overflow-y-auto">
          {/* AI Interviewer Avatar Tile with Realistic Neural Persona */}
          <InterviewerAvatar
            isSpeaking={isSpeaking}
            frequencyLevel={frequencyLevel}
            persona={selectedPersona}
            targetCompany={sessionData?.target_company}
            currentStage={fsmSnapshot?.current_stage || "INTRO"}
            isCandidateWorking={isCandidateWorking}
            isInterviewerThinking={isInterviewerThinking}
          />

          {/* Candidate Webcam Tile with Local-only Presence */}
          <CandidateWebcam
            isMicMuted={isMicMuted}
            onMuteToggle={(muted) => setIsMicMuted(muted)}
            startTime={sessionData?.created_at}
          />

          {/* Live Transcript / Subtitles & Turn Dispatching */}
          <div className="flex-1 min-h-[240px] rounded-2xl glass-panel border border-slate-800 bg-slate-900/80 p-3.5 flex flex-col justify-between overflow-hidden shadow-xl">
            <div className="overflow-y-auto flex-1 pr-1 space-y-2.5 max-h-[220px]">
              <div className="flex items-center justify-between sticky top-0 bg-slate-900/90 backdrop-blur pb-1 z-10 border-b border-slate-800/60">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Live Conversational Stream
                </span>
                <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Multimodal Live Room
                </span>
              </div>

              {transcripts.length === 0 ? (
                <div className="p-3 text-center text-xs text-slate-400 space-y-1">
                  <p className="font-semibold text-slate-300">Connecting to your interviewer...</p>
                  <p className="text-[11px] text-slate-500">
                    Feel free to speak into your microphone or type in the response bar below.
                  </p>
                </div>
              ) : (
                transcripts.map((turn, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl text-xs leading-relaxed transition-all ${
                      turn.speaker === "interviewer"
                        ? "bg-blue-950/40 border border-blue-800/40 text-blue-100"
                        : "bg-slate-950/80 border border-slate-800 text-slate-200 ml-4"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">
                        {turn.speaker === "interviewer" ? selectedPersona.name : "You (Candidate)"}
                      </span>
                      {turn.time && <span className="text-[9px] text-slate-500">{turn.time}</span>}
                    </div>
                    <p className="whitespace-pre-wrap">{turn.text}</p>
                  </div>
                ))
              )}

              {/* Real-time Interviewer Thinking Indicator */}
              {isInterviewerThinking && (
                <div className="p-2.5 rounded-xl text-xs bg-indigo-950/40 border border-indigo-800/40 text-indigo-300 flex items-center gap-2 animate-pulse">
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
                  <span>{selectedPersona.name} is listening & synthesizing evaluation...</span>
                </div>
              )}

              {/* Silence & Encouragement Banner */}
              {silencePrompt && !isSpeaking && (
                <div className="p-2.5 rounded-xl text-xs bg-amber-500/10 border border-amber-500/20 text-amber-200 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>{silencePrompt}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      handleSendDirectPrompt(
                        "I'm formulating my response, could you give me a minute or a quick hint?"
                      )
                    }
                    className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[10px] font-semibold whitespace-nowrap transition-colors"
                  >
                    Need Hint
                  </button>
                </div>
              )}

              <div ref={transcriptEndRef} />
            </div>

            {/* Turn-Taking & Response Control Section */}
            <div className="pt-2 border-t border-slate-800/60 flex flex-col gap-2">
              {/* Quick Action Suggestion Chips */}
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() =>
                    handleSendDirectPrompt("Can you explain the problem and requirements in detail?")
                  }
                  className="px-2.5 py-1 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 hover:text-white transition-colors"
                >
                  Explain Question
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleSendDirectPrompt("Could you clarify the input constraints and edge cases?")
                  }
                  className="px-2.5 py-1 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 hover:text-white transition-colors"
                >
                  Clarify Constraints
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleSendDirectPrompt("I'm thinking through my approach, could you give me a targeted hint?")
                  }
                  className="px-2.5 py-1 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 hover:text-white transition-colors"
                >
                  Get Hint
                </button>
                {isSpeaking && (
                  <button
                    type="button"
                    onClick={handleInterrupt}
                    className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-[10px] text-amber-300 font-bold transition-colors ml-auto flex items-center gap-1 animate-pulse"
                  >
                    <Hand className="w-2.5 h-2.5" /> Cut In (Space)
                  </button>
                )}
              </div>

              {/* Live Speech Recognition Preview Banner */}
              {liveSpeechPreview && (
                <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl bg-blue-950/80 border border-blue-500/40 text-blue-200 text-xs shadow-lg shadow-blue-950/40">
                  <div className="flex items-center gap-2 overflow-hidden flex-1">
                    <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping shrink-0" />
                    <span className="font-semibold text-blue-300 text-[10px] uppercase tracking-wider shrink-0">
                      Hearing:
                    </span>
                    <span className="truncate italic text-slate-100 font-medium">
                      &ldquo;{liveSpeechPreview}&rdquo;
                    </span>
                    {pauseCountdown !== null && pauseCountdown > 0 && voiceInputMode === "handsfree" && (
                      <span className="text-[10px] text-amber-400 font-semibold px-1.5 py-0.5 rounded bg-amber-500/10">
                        Sending in {pauseCountdown}s
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => dispatchCandidateTurn(liveSpeechPreview)}
                      className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-[10px] transition-colors flex items-center gap-1 shadow-sm"
                      title="Send spoken answer now"
                    >
                      <Send className="w-2.5 h-2.5" /> Done Speaking (Enter)
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setLiveSpeechPreview("");
                        speechBufferRef.current = "";
                        setPauseCountdown(null);
                      }}
                      className="p-1 rounded-lg hover:bg-blue-900/50 text-slate-400 hover:text-slate-200 transition-colors"
                      title="Discard speech"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              )}

              {/* Push-to-Talk Status Indicator */}
              {voiceInputMode === "push_to_talk" && (
                <div
                  onMouseDown={() => {
                    setIsPushToTalkActive(true);
                    setIsMicMuted(false);
                  }}
                  onMouseUp={() => {
                    setIsPushToTalkActive(false);
                    if (speechBufferRef.current.trim().length > 0) {
                      dispatchCandidateTurn(speechBufferRef.current.trim());
                    }
                  }}
                  onTouchStart={() => {
                    setIsPushToTalkActive(true);
                    setIsMicMuted(false);
                  }}
                  onTouchEnd={() => {
                    setIsPushToTalkActive(false);
                    if (speechBufferRef.current.trim().length > 0) {
                      dispatchCandidateTurn(speechBufferRef.current.trim());
                    }
                  }}
                  className={`w-full py-2 px-3 rounded-xl border flex items-center justify-center gap-2 cursor-pointer transition-all select-none ${
                    isPushToTalkActive
                      ? "bg-rose-600 border-rose-400 text-white font-bold shadow-lg shadow-rose-600/30 scale-[0.99]"
                      : "bg-slate-900/90 border-slate-700/80 text-slate-300 hover:bg-slate-850 hover:text-white"
                  }`}
                >
                  <Mic className={`w-4 h-4 ${isPushToTalkActive ? "animate-bounce" : "text-blue-400"}`} />
                  <span className="text-xs font-semibold">
                    {isPushToTalkActive
                      ? "Listening... Release when done speaking"
                      : "Hold Spacebar or Click & Hold to Speak"}
                  </span>
                </div>
              )}

              {/* Candidate Response Input Form */}
              <form onSubmit={handleSendCandidateText} className="flex items-center gap-2">
                <input
                  type="text"
                  value={candidateInputText}
                  onChange={(e) => setCandidateInputText(e.target.value)}
                  placeholder={
                    voiceInputMode === "handsfree"
                      ? "Speak freely into microphone or type your answer..."
                      : "Type answer or hold Spacebar to talk..."
                  }
                  className="flex-1 bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none transition-colors"
                />

                {/* Mic Indicator / Toggle */}
                <button
                  type="button"
                  onClick={() => setIsMicMuted(!isMicMuted)}
                  className={`px-2.5 py-1.5 rounded-xl border flex items-center gap-1.5 text-[11px] font-semibold transition-all ${
                    isMicMuted
                      ? "bg-rose-950/30 border-rose-800/40 text-rose-400 hover:bg-rose-950/50"
                      : "bg-emerald-950/40 border-emerald-800/40 text-emerald-400 hover:bg-emerald-950/60"
                  }`}
                  title={isMicMuted ? "Click to unmute microphone" : "Click to mute microphone"}
                >
                  {isMicMuted ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5 animate-pulse" />}
                  <span className="hidden sm:inline">{isMicMuted ? "Muted" : "Live"}</span>
                </button>

                <button
                  type="submit"
                  disabled={!candidateInputText.trim()}
                  className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white transition-colors"
                  title="Send answer"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right Pane (62% width - Interactive Technical Workbench) */}
        <div className="w-[62%] bg-slate-950 flex flex-col overflow-hidden">
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
                <FileQuestion className="w-3.5 h-3.5" /> Problem & Theory Rubric
              </button>
            </div>

            {/* Next Problem Switcher */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSwitchQuestion}
                disabled={isSwitchingQuestion}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors border border-slate-700/60"
                title="Switch to another problem from the question bank"
              >
                <Shuffle className={`w-3.5 h-3.5 text-blue-400 ${isSwitchingQuestion ? "animate-spin" : ""}`} />
                <span>{isSwitchingQuestion ? "Switching..." : "Next Problem"}</span>
              </button>
            </div>
          </div>

          {/* Workbench Tab Content */}
          <div className="flex-1 p-3 overflow-hidden">
            {activeTab === "code" && (
              <CodeSandbox
                initialLanguage={activeQuestion?.category === "SQL" ? "sql" : "python"}
                initialCode={activeQuestion?.starter_code || "# Write your Python solution here\n"}
                seedSql={activeQuestion?.seed_sql}
                unitTests={activeQuestion?.unit_tests}
                activeQuestion={activeQuestion}
                onAskInterviewer={handleSendDirectPrompt}
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
