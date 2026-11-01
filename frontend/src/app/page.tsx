"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  ShieldCheck,
  FileText,
  Briefcase,
  Key,
  Layers,
  ArrowRight,
  Code,
  Cpu,
  Database,
  CheckCircle,
} from "lucide-react";

export default function OnboardingPage() {
  const router = useRouter();

  const [apiKey, setApiKey] = useState("");
  const [targetRole, setTargetRole] = useState("Senior Machine Learning Engineer");
  const [targetCompany, setTargetCompany] = useState("Google");
  const [interviewMode, setInterviewMode] = useState("FULL_LOOP");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
    }
  };

  const handleStartInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    // Persist API key in sessionStorage for BYOK security
    if (apiKey.trim()) {
      sessionStorage.setItem("ai_interviewer_api_key", apiKey.trim());
    }

    try {
      const formData = new FormData();
      if (resumeFile) {
        formData.append("resume_file", resumeFile);
      }
      formData.append("target_role", targetRole);
      formData.append("target_company", targetCompany);
      formData.append("interview_mode", interviewMode);
      if (jobDescription.trim()) {
        formData.append("job_description", jobDescription.trim());
      }
      if (apiKey.trim()) {
        formData.append("api_key", apiKey.trim());
      }

      const res = await fetch("http://localhost:8000/api/session/init", {
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
      setErrorMsg(err.message || "Failed to initialize interview session. Ensure backend is running.");
    } finally {
      setIsLoading(false);
    }
  };

  const modes = [
    {
      id: "FULL_LOOP",
      title: "Full Loop (Complete)",
      desc: "All 5 stages: Intro → Resume Deep-Dive → Coding (SQL/Python) → ML System Design → Wrap-Up",
      icon: Layers,
    },
    {
      id: "RESUME_DEEP_DIVE",
      title: "Resume Bar-Raiser",
      desc: "3-layer grilling probes on technical metrics, leakage, latency SLAs, and drift",
      icon: FileText,
    },
    {
      id: "SQL_PYTHON_CODING",
      title: "SQL & Python Coding",
      desc: "Live Monaco IDE with in-browser DuckDB-WASM and Pyodide WebAssembly",
      icon: Code,
    },
    {
      id: "ML_SYSTEM_DESIGN",
      title: "ML System Design",
      desc: "Interactive architecture whiteboard for high-throughput feature stores and ranking funnels",
      icon: Cpu,
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
              Privacy-First Multimodal Bar-Raiser
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Local-First & BYOK</span>
        </div>
      </header>

      {/* Hero & Setup Form */}
      <div className="max-w-4xl mx-auto w-full my-8 z-10">
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-slate-400 tracking-tight">
            Rigorous Interview Preparation for Senior ML & DS
          </h1>
          <p className="text-slate-400 text-sm md:text-base mt-3 max-w-2xl mx-auto leading-relaxed">
            Zero sycophancy. Realistic 3-layer deep technical probing. Powered by Gemini Multimodal Live,
            Pyodide, and DuckDB-WASM running 100% private on your machine.
          </p>
        </div>

        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleStartInterview} className="space-y-6">
          {/* Section 1: BYOK API Key & Privacy */}
          <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Key className="w-4 h-4 text-blue-400" /> Gemini API Key (BYOK)
              </label>
              <span className="text-[11px] text-slate-500">Optional if set in backend .env</span>
            </div>
            <input
              type="password"
              placeholder="AIzaSy... (Stored in browser sessionStorage only)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-colors font-mono"
            />
          </div>

          {/* Section 2: Target Position & Company */}
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
                placeholder="e.g. Google, Stripe, Meta, Netflix"
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Section 3: Resume Upload */}
          <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-blue-400" /> Upload PDF Resume
            </label>
            <p className="text-xs text-slate-400 mb-3">
              PyMuPDF extracts your technical claim graph to formulate realistic bar-raiser probes.
            </p>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="w-full text-xs text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
            />
          </div>

          {/* Section 4: Interview Mode Selector */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 block pl-1">
              Select Interview Track
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {modes.map((m) => {
                const Icon = m.icon;
                const isSelected = interviewMode === m.id;
                return (
                  <div
                    key={m.id}
                    onClick={() => setInterviewMode(m.id)}
                    className={`p-4 rounded-2xl cursor-pointer transition-all border ${
                      isSelected
                        ? "bg-blue-600/10 border-blue-500 shadow-lg shadow-blue-500/10"
                        : "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className={`p-2 rounded-lg ${
                            isSelected ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <h3 className="text-sm font-semibold text-slate-200">{m.title}</h3>
                      </div>
                      {isSelected && <CheckCircle className="w-4 h-4 text-blue-400" />}
                    </div>
                    <p className="text-xs text-slate-400 pl-1">{m.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-4 rounded-2xl text-base font-bold text-white flex items-center justify-center gap-2 transition-all shadow-xl ${
              isLoading
                ? "bg-blue-800 cursor-not-allowed"
                : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-600/30"
            }`}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing Resume & Initializing Interview Room...
              </span>
            ) : (
              <>
                Enter Live Interview Room <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
      </div>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto w-full text-center text-xs text-slate-500 pt-6 border-t border-slate-900 z-10">
        ai-interviewer • Open-Source Local-First Technical Evaluation Platform
      </footer>
    </main>
  );
}
