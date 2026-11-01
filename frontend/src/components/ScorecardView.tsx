"use client";

import React, { useState } from "react";
import {
  Award,
  TrendingUp,
  Code2,
  MessageSquare,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowRight,
} from "lucide-react";

export interface ScorecardData {
  overall_score: number;
  recommendation: string;
  summary: string;
  key_strengths: string[];
  critical_improvement_areas: string[];
  technical_depth: {
    dimension: string;
    score: number;
    rationale: string;
    strengths?: string[];
    weaknesses?: string[];
  };
  production_tradeoffs: {
    dimension: string;
    score: number;
    rationale: string;
    strengths?: string[];
    weaknesses?: string[];
  };
  code_quality: {
    dimension: string;
    score: number;
    rationale: string;
    strengths?: string[];
    weaknesses?: string[];
  };
  communication_clarity: {
    dimension: string;
    score: number;
    rationale: string;
    strengths?: string[];
    weaknesses?: string[];
  };
  question_critiques: Array<{
    question_asked: string;
    candidate_answer_summary: string;
    hiring_manager_critique: string;
    gold_standard_rewrite: string;
  }>;
}

interface ScorecardViewProps {
  data: ScorecardData;
}

export default function ScorecardView({ data }: ScorecardViewProps) {
  const [selectedCritiqueIdx, setSelectedCritiqueIdx] = useState(0);

  const dimensions = [
    {
      title: "Technical Depth & Math",
      icon: Award,
      data: data.technical_depth,
      color: "from-blue-500 to-indigo-500",
    },
    {
      title: "Production & Business Trade-offs",
      icon: TrendingUp,
      data: data.production_tradeoffs,
      color: "from-emerald-500 to-teal-500",
    },
    {
      title: "Code / SQL Quality & Complexity",
      icon: Code2,
      data: data.code_quality,
      color: "from-violet-500 to-purple-500",
    },
    {
      title: "Communication Clarity (STAR)",
      icon: MessageSquare,
      data: data.communication_clarity,
      color: "from-amber-500 to-orange-500",
    },
  ];

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Top Banner: Overall Score & Recommendation */}
      <div className="p-8 rounded-3xl glass-panel border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900/90 to-blue-950/40 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="w-3.5 h-3.5" /> BARS Evaluated Scorecard
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
            Interview Performance Report
          </h1>
          <p className="text-slate-400 text-sm mt-2 max-w-xl leading-relaxed">
            {data.summary}
          </p>
        </div>

        {/* Score Badge */}
        <div className="flex items-center gap-6 p-4 rounded-2xl bg-slate-950/70 border border-slate-800">
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
              {data.overall_score.toFixed(1)}
              <span className="text-xl text-slate-500 font-normal"> / 5.0</span>
            </div>
            <p className="text-xs font-medium text-slate-400 mt-1 uppercase tracking-wider">
              Overall Rating
            </p>
          </div>

          <div className="h-12 w-px bg-slate-800" />

          <div className="text-center pr-2">
            <span
              className={`inline-block px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                data.recommendation.toLowerCase().includes("hire")
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
              }`}
            >
              {data.recommendation}
            </span>
            <p className="text-xs font-medium text-slate-400 mt-1 uppercase tracking-wider">
              Verdict
            </p>
          </div>
        </div>
      </div>

      {/* 4 BARS Dimensions Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {dimensions.map((dim, i) => {
          const Icon = dim.icon;
          return (
            <div
              key={i}
              className="p-5 rounded-2xl glass-panel border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 rounded-xl bg-slate-800 border border-slate-700/60 text-slate-200">
                    <Icon className="w-5 h-5 text-blue-400" />
                  </div>
                  <div className="text-2xl font-bold text-white">
                    {dim.data.score}
                    <span className="text-xs text-slate-500 font-normal"> / 5</span>
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-slate-200">{dim.title}</h3>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                  {dim.data.rationale}
                </p>
              </div>

              {/* Progress bar */}
              <div className="mt-4 pt-3 border-t border-slate-800/80">
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${dim.color}`}
                    style={{ width: `${(dim.data.score / 5) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Key Strengths & Critical Improvements */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strengths */}
        <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/50">
          <h3 className="text-base font-semibold text-emerald-400 flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5" /> Key Technical Strengths
          </h3>
          <ul className="space-y-2.5">
            {data.key_strengths.map((str, idx) => (
              <li
                key={idx}
                className="text-xs text-slate-300 flex items-start gap-2.5 bg-slate-950/40 p-3 rounded-xl border border-slate-800/60 leading-relaxed"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                <span>{str}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Improvements */}
        <div className="p-6 rounded-2xl glass-panel border border-slate-800 bg-slate-900/50">
          <h3 className="text-base font-semibold text-amber-400 flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5" /> Critical Improvement Areas
          </h3>
          <ul className="space-y-2.5">
            {data.critical_improvement_areas.map((imp, idx) => (
              <li
                key={idx}
                className="text-xs text-slate-300 flex items-start gap-2.5 bg-slate-950/40 p-3 rounded-xl border border-slate-800/60 leading-relaxed"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                <span>{imp}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Question-by-Question Diff & Gold-Standard STAR Rewrites */}
      {data.question_critiques && data.question_critiques.length > 0 && (
        <div className="p-6 rounded-3xl glass-panel border border-slate-800 bg-slate-900/80 shadow-2xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" /> Question-by-Question Deep Critique & STAR Rewrites
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Side-by-side comparison between your response and a Staff-level 60-second delivery.
              </p>
            </div>

            {/* Critique Selector Tabs */}
            <div className="flex items-center gap-1.5">
              {data.question_critiques.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSelectedCritiqueIdx(idx)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    selectedCritiqueIdx === idx
                      ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                      : "bg-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Q{idx + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Active Critique Content */}
          {data.question_critiques[selectedCritiqueIdx] && (
            <div className="space-y-5">
              {/* Question Asked Header */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">
                  Question Asked
                </span>
                <p className="text-sm font-medium text-slate-100 mt-1">
                  &ldquo;{data.question_critiques[selectedCritiqueIdx].question_asked}&rdquo;
                </p>
              </div>

              {/* Side-by-Side Comparison */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Candidate Said + Critique */}
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      What You Said (Summary)
                    </span>
                    <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">
                      {data.question_critiques[selectedCritiqueIdx].candidate_answer_summary}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-900/30">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" /> Hiring Manager Critique
                    </span>
                    <p className="text-xs text-rose-200/90 mt-1.5 leading-relaxed">
                      {data.question_critiques[selectedCritiqueIdx].hiring_manager_critique}
                    </p>
                  </div>
                </div>

                {/* Gold-Standard STAR Rewrite */}
                <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-950/30 via-slate-950 to-blue-950/30 border border-indigo-800/50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" /> Staff-Level 60-Second Rewrite
                      </span>
                      <span className="text-[10px] text-slate-500 font-medium">STAR Framework</span>
                    </div>

                    <p className="text-xs text-indigo-100/90 leading-relaxed italic mt-2">
                      &ldquo;{data.question_critiques[selectedCritiqueIdx].gold_standard_rewrite}&rdquo;
                    </p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-indigo-900/40 text-[11px] text-indigo-300/70">
                    💡 Mentorship Tip: Lead directly with the quantifiable metric outcome before detailing architectural nuances.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
