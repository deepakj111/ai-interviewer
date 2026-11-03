"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  ShieldCheck,
  FileText,
  Key,
  Layers,
  ArrowRight,
  Code,
  Cpu,
  CheckCircle,
  Radio,
  UserCheck,
  Globe,
  UploadCloud,
  X,
  Play,
  Zap,
  Activity,
} from "lucide-react";
import { INTERVIEWER_PERSONAS, voiceManager } from "@/lib/voiceManager";
import { getApiUrl, checkBackendHealth } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();

  const [apiKey, setApiKey] = useState("");
  const [selectedPersonaId, setSelectedPersonaId] = useState("elena");
  const [isTestingVoice, setIsTestingVoice] = useState(false);
  const [targetRole, setTargetRole] = useState("Senior Machine Learning Engineer");
  const [targetCompany, setTargetCompany] = useState("Swiggy");
  const [companyArchetype, setCompanyArchetype] = useState("INDIAN_PRODUCT");
  const [enableLiveWebSearch, setEnableLiveWebSearch] = useState(true);
  const [interviewMode, setInterviewMode] = useState("ML_BREADTH");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [availableQuestions, setAvailableQuestions] = useState<any[]>([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Live Backend Connection Status
  const [backendHealth, setBackendHealth] = useState<{
    ok: boolean;
    latencyMs: number;
    statusText: string;
  } | null>(null);

  useEffect(() => {
    async function pingBackend() {
      const health = await checkBackendHealth();
      setBackendHealth(health);
    }
    pingBackend();
    const interval = setInterval(pingBackend, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    async function loadQuestions() {
      try {
        const res = await fetch(getApiUrl("/api/questions"));
        if (res.ok) {
          const qs = await res.json();
          setAvailableQuestions(qs);
        }
      } catch (e) {
        console.warn("Could not load questions catalog:", e);
      }
    }
    loadQuestions();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
      setInterviewMode("FULL_LOOP");
    }
  };

  const handleRemoveResume = () => {
    setResumeFile(null);
    if (interviewMode === "FULL_LOOP" || interviewMode === "RESUME_DEEP_DIVE") {
      setInterviewMode("ML_BREADTH");
    }
  };

  const companyPresets = [
    { name: "Swiggy", archetype: "INDIAN_PRODUCT", role: "Senior Machine Learning Engineer" },
    { name: "Zomato", archetype: "INDIAN_PRODUCT", role: "Senior Applied Scientist" },
    { name: "CRED", archetype: "INDIAN_PRODUCT", role: "Senior Data Scientist" },
    { name: "Razorpay", archetype: "INDIAN_PRODUCT", role: "Staff Machine Learning Engineer" },
    { name: "Google", archetype: "FAANG_GLOBAL", role: "Senior Machine Learning Engineer" },
    { name: "Meta", archetype: "FAANG_GLOBAL", role: "Research / Applied Scientist" },
    { name: "Stripe", archetype: "FAANG_GLOBAL", role: "Staff Infrastructure Engineer" },
    { name: "AI Startup", archetype: "AI_STARTUP", role: "Lead AI / LLM Engineer" },
  ];

  const handleSelectPreset = (preset: { name: string; archetype: string; role: string }) => {
    setTargetCompany(preset.name);
    setCompanyArchetype(preset.archetype);
    setTargetRole(preset.role);
  };

  const handleStartInterview = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    if ((interviewMode === "FULL_LOOP" || interviewMode === "RESUME_DEEP_DIVE") && !resumeFile) {
      setErrorMsg(
        "Please upload a PDF resume for tracks with Resume Probing, or select ML Breadth, ML Depth, GenAI, or Coding."
      );
      setIsLoading(false);
      return;
    }

    if (apiKey.trim()) {
      sessionStorage.setItem("ai_interviewer_api_key", apiKey.trim());
    }
    sessionStorage.setItem("ai_interviewer_persona", selectedPersonaId);
    voiceManager.setPersona(selectedPersonaId);

    try {
      const formData = new FormData();
      if (resumeFile) {
        formData.append("resume_file", resumeFile);
      }
      formData.append("target_role", targetRole);
      formData.append("target_company", targetCompany);
      formData.append("company_archetype", companyArchetype);
      formData.append("enable_live_web_search", enableLiveWebSearch ? "true" : "false");
      formData.append("interview_mode", interviewMode);
      if (jobDescription.trim()) {
        formData.append("job_description", jobDescription.trim());
      }
      if (apiKey.trim()) {
        formData.append("api_key", apiKey.trim());
      }
      if (selectedQuestionId.trim()) {
        formData.append("question_id", selectedQuestionId.trim());
      }

      const res = await fetch(getApiUrl("/api/session/init"), {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session: ${res.statusText}`);
      }

      const data = await res.json();
      router.push(`/interview/${data.session_id}`);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(
        err.message || "Failed to initialize interview session. Ensure the backend server is running."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLaunch = () => {
    setInterviewMode("ML_BREADTH");
    setTargetCompany("Google");
    setCompanyArchetype("FAANG_GLOBAL");
    setTargetRole("Senior Machine Learning Engineer");
    handleStartInterview();
  };

  const handleTestVoice = (personaId: string) => {
    if (isTestingVoice) return;
    setIsTestingVoice(true);
    voiceManager.setPersona(personaId);
    const persona = voiceManager.getPersona();
    voiceManager.speak(
      `Hello! I'm ${persona.name}. I'm ready to conduct your technical interview.`,
      {
        onEnd: () => setIsTestingVoice(false),
      }
    );
  };

  const modes = [
    {
      id: "ML_BREADTH",
      title: "ML Breadth Round",
      desc: "Rapid-fire foundational ML: bias-variance, regularizations (L1/L2), loss formulations, trees vs nets, and metrics",
      icon: Layers,
      requiresResume: false,
    },
    {
      id: "ML_DEPTH",
      title: "ML Depth Round",
      desc: "Deep mathematical derivations: analytical loss gradients, attention matrices, FlashAttention, and LoRA mechanics",
      icon: Cpu,
      requiresResume: false,
    },
    {
      id: "GENERATIVE_AI_LLM",
      title: "Generative AI & LLM Track",
      desc: "Production GenAI: RAG chunking & hybrid retrieval, LoRA/DPO fine-tuning, KV cache optimization, and guardrails",
      icon: Sparkles,
      requiresResume: false,
    },
    {
      id: "SQL_PYTHON_CODING",
      title: "SQL & Python Coding",
      desc: "Live Monaco IDE with in-browser DuckDB-WASM and Pyodide WebAssembly",
      icon: Code,
      requiresResume: false,
    },
    {
      id: "ML_SYSTEM_DESIGN",
      title: "ML System Design",
      desc: "Interactive architecture whiteboard for high-throughput feature stores and ranking funnels",
      icon: Cpu,
      requiresResume: false,
    },
    {
      id: "FULL_LOOP",
      title: "Full Loop (Comprehensive)",
      desc: "Complete 45-min loop: Intro → Resume Probing → Coding (SQL/Python) → ML System Design → Wrap-Up",
      icon: Layers,
      requiresResume: true,
    },
    {
      id: "RESUME_DEEP_DIVE",
      title: "Resume Bar-Raiser",
      desc: "3-layer grilling probes on technical metrics, leakage, latency SLAs, and drift",
      icon: FileText,
      requiresResume: true,
    },
  ];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between p-6 md:p-12 relative overflow-hidden">
      {/* Background Glow Orbs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header Bar */}
      <header className="max-w-6xl mx-auto w-full flex items-center justify-between pb-8 border-b border-slate-800/80 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-black tracking-tight text-white">ai-interviewer</span>
            <span className="block text-[11px] text-blue-400 font-medium">
              Multimodal Technical Bar-Raiser (2026 Edition)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Backend Status Pill */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold ${
              backendHealth?.ok
                ? "bg-emerald-950/50 border-emerald-800/50 text-emerald-300"
                : "bg-amber-950/40 border-amber-800/40 text-amber-300"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendHealth?.ok ? "bg-emerald-400 animate-pulse" : "bg-amber-400 animate-ping"
              }`}
            />
            <span>
              {backendHealth?.ok
                ? `Backend Online (${backendHealth.latencyMs}ms)`
                : "Checking Backend..."}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Local-First & BYOK</span>
          </div>
        </div>
      </header>

      {/* Hero & Setup Form */}
      <div className="max-w-4xl mx-auto w-full my-8 z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Zap className="w-3.5 h-3.5" /> Next-Gen AI Interview Simulation
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-slate-400 tracking-tight">
            Rigorous Interview Preparation for Senior ML & DS
          </h1>
          <p className="text-slate-400 text-sm md:text-base mt-3 max-w-2xl mx-auto leading-relaxed">
            Realistic turn-taking dialogue, photorealistic AI interviewer personas, zero sycophancy,
            in-browser Monaco IDE with DuckDB and Pyodide, and post-interview BARS scorecards.
          </p>

          {/* Quick Demo Launch Button */}
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleQuickDemoLaunch}
              disabled={isLoading}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-sm shadow-xl shadow-blue-500/25 flex items-center gap-2 transition-all transform hover:scale-[1.02]"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Instant 1-Click Practice Demo</span>
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center justify-between">
            <span>{errorMsg}</span>
            <button type="button" onClick={() => setErrorMsg(null)} className="p-1 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <form onSubmit={handleStartInterview} className="space-y-6">
          {/* Section 1: Choose Your AI Interviewer Persona */}
          <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-blue-400" /> Select Your AI Interviewer
              </label>
              <span className="text-[11px] text-slate-400">Photorealistic Neural Personas</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {INTERVIEWER_PERSONAS.map((persona) => {
                const isSelected = selectedPersonaId === persona.id;
                return (
                  <div
                    key={persona.id}
                    onClick={() => setSelectedPersonaId(persona.id)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col items-center text-center relative overflow-hidden ${
                      isSelected
                        ? "bg-blue-600/15 border-blue-500 shadow-xl shadow-blue-500/15 ring-1 ring-blue-400"
                        : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-2 right-2 p-1 rounded-full bg-blue-500 text-white">
                        <CheckCircle className="w-3.5 h-3.5" />
                      </div>
                    )}

                    <div className="relative w-20 h-20 rounded-full overflow-hidden mb-3 border-2 border-slate-700 shadow-md">
                      <Image
                        src={persona.avatarImage}
                        alt={persona.name}
                        fill
                        className="object-cover object-top"
                      />
                    </div>

                    <h3 className="font-bold text-sm text-slate-100">{persona.name}</h3>
                    <span className="text-[11px] text-blue-400 font-semibold mb-1">
                      {persona.title}
                    </span>
                    <p className="text-[11px] text-slate-400 leading-snug line-clamp-3 mb-3">
                      {persona.description}
                    </p>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTestVoice(persona.id);
                      }}
                      className="mt-auto px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-300 font-semibold flex items-center gap-1 transition-colors"
                    >
                      <Radio className="w-3 h-3 text-blue-400" />
                      <span>Preview Voice</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 2: BYOK API Key (Optional) */}
          <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Key className="w-4 h-4 text-blue-400" /> Gemini API Key (BYOK)
              </label>
              <span className="text-[11px] text-emerald-400 font-medium">
                Optional — 100% Functional Zero-Key Offline Mode Included
              </span>
            </div>
            <input
              type="password"
              placeholder="AIzaSy... (Optional: leave blank for zero-key local mode)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-colors font-mono"
            />
          </div>

          {/* Section 3: Target Position, Company & Engineering Archetype */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block mb-2">
                  Target Role
                </label>
                <input
                  type="text"
                  required
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Machine Learning Engineer"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="p-5 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block mb-2">
                  Target Company
                </label>
                <input
                  type="text"
                  required
                  value={targetCompany}
                  onChange={(e) => setTargetCompany(e.target.value)}
                  placeholder="e.g. Swiggy, CRED, Google, Stripe"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {/* Quick Company Presets */}
            <div className="flex flex-wrap items-center gap-1.5 px-1">
              <span className="text-[11px] font-semibold text-slate-400 mr-1">Quick Presets:</span>
              {companyPresets.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => handleSelectPreset(preset)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all border ${
                    targetCompany.toLowerCase() === preset.name.toLowerCase()
                      ? "bg-blue-600/30 border-blue-500 text-blue-200"
                      : "bg-slate-900/80 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {preset.name}
                </button>
              ))}
            </div>

            {/* Company Archetype Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              {[
                {
                  id: "INDIAN_PRODUCT",
                  title: "🇮🇳 Indian Product Tech",
                  subtitle: "Swiggy, CRED, Zomato, Razorpay",
                  desc: "Hyperlocal surges, UPI fraud, high concurrency, pragmatic unit economics",
                },
                {
                  id: "FAANG_GLOBAL",
                  title: "🏢 Global Tech / FAANG",
                  subtitle: "Google, Meta, Stripe, Netflix",
                  desc: "Massive distributed scale, formal p99 latency SLAs, statistical depth",
                },
                {
                  id: "AI_STARTUP",
                  title: "🚀 AI Startups & Labs",
                  subtitle: "Perplexity, Cursor, Agentic AI",
                  desc: "Rapid velocity, vLLM cost optimization, agent tool-calling, pragmatism",
                },
              ].map((arch) => {
                const isSelected = companyArchetype === arch.id;
                return (
                  <div
                    key={arch.id}
                    onClick={() => setCompanyArchetype(arch.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-600/10 border-blue-500 shadow-md shadow-blue-500/10"
                        : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-200">{arch.title}</span>
                      {isSelected && <CheckCircle className="w-3.5 h-3.5 text-blue-400" />}
                    </div>
                    <span className="text-[11px] text-blue-400 font-medium block mb-1">
                      {arch.subtitle}
                    </span>
                    <p className="text-[11px] text-slate-400 leading-snug">{arch.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 4: Select Interview Track */}
          <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block mb-4">
              Select Interview Track
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {modes.map((mode) => {
                const isSelected = interviewMode === mode.id;
                const Icon = mode.icon;
                return (
                  <div
                    key={mode.id}
                    onClick={() => setInterviewMode(mode.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                      isSelected
                        ? "bg-blue-600/15 border-blue-500 shadow-md shadow-blue-500/10"
                        : "bg-slate-950/40 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div
                      className={`p-2 rounded-lg ${
                        isSelected ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-slate-200">{mode.title}</span>
                        {isSelected && <CheckCircle className="w-3.5 h-3.5 text-blue-400" />}
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug">{mode.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 5: Resume Upload (Required for Full Loop & Resume Probing) */}
          {(interviewMode === "FULL_LOOP" || interviewMode === "RESUME_DEEP_DIVE") && (
            <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block mb-3">
                Upload Candidate PDF Resume
              </label>

              {!resumeFile ? (
                <label className="border-2 border-dashed border-slate-800 hover:border-blue-500/50 rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-950/50">
                  <UploadCloud className="w-8 h-8 text-slate-500 mb-2" />
                  <span className="text-xs font-semibold text-slate-300">
                    Click to browse or drop your PDF resume here
                  </span>
                  <span className="text-[10px] text-slate-500 mt-1">
                    Processed 100% locally to extract candidate claim graph & technical projects
                  </span>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </label>
              ) : (
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="flex items-center gap-2.5">
                    <FileText className="w-5 h-5 text-blue-400" />
                    <div>
                      <p className="text-xs font-semibold text-slate-200">{resumeFile.name}</p>
                      <p className="text-[10px] text-slate-500">
                        {(resumeFile.size / 1024).toFixed(1)} KB — Ready for analysis
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveResume}
                    className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Launch Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-sm shadow-xl shadow-blue-600/25 flex items-center justify-center gap-2 transition-all transform hover:scale-[1.01]"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Preparing Interview Room...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                Launch Interview Session <ArrowRight className="w-4 h-4" />
              </span>
            )}
          </button>
        </form>
      </div>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full pt-8 border-t border-slate-800/80 text-center text-xs text-slate-500 z-10">
        ai-interviewer • Built for Senior Data Scientists & ML Engineers • 100% Local-First
      </footer>
    </main>
  );
}
