"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Sparkles, RefreshCw } from "lucide-react";
import ScorecardView, { ScorecardData } from "@/components/ScorecardView";
import { getApiUrl } from "@/lib/api";

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [report, setReport] = useState<ScorecardData | null>(null);
  const [transcripts, setTranscripts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchOrGenerateReport() {
      if (!sessionId) return;
      setLoading(true);
      setError(null);

      try {
        const apiKey = typeof window !== "undefined" ? sessionStorage.getItem("ai_interviewer_api_key") || "" : "";
        // First try getting existing report
        let res = await fetch(getApiUrl(`/api/session/${sessionId}/report`));
        if (!res.ok) {
          // If not generated yet, trigger evaluation
          res = await fetch(
            getApiUrl(`/api/session/${sessionId}/evaluate${apiKey ? `?api_key=${apiKey}` : ""}`),
            { method: "POST" }
          );
        }

        if (!res.ok) {
          throw new Error("Failed to generate BARS evaluation report");
        }

        const data = await res.json();
        setReport(data);

        // Fetch complete interview transcripts for review log
        try {
          const tRes = await fetch(getApiUrl(`/api/session/${sessionId}/transcripts`));
          if (tRes.ok) {
            const tData = await tRes.json();
            setTranscripts(tData);
          }
        } catch (tErr) {
          console.warn("Could not fetch transcripts log:", tErr);
        }
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Could not load evaluation report");
      } finally {
        setLoading(false);
      }
    }

    fetchOrGenerateReport();
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-12">
      {/* Top Navigation */}
      <div className="max-w-6xl mx-auto flex items-center justify-between pb-8 mb-8 border-b border-slate-800/80">
        <button
          type="button"
          onClick={() => router.push("/")}
          className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-2 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Dashboard
        </button>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-blue-400 font-medium">
          <Sparkles className="w-4 h-4" /> Senior Mentor Evaluation
        </div>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-4" />
          <h2 className="text-xl font-bold text-white">Grading Interview Transcripts...</h2>
          <p className="text-xs text-slate-400 mt-2 max-w-md">
            The Senior Mentor Persona is reviewing your technical depth, production trade-offs, code execution,
            and formatting STAR rewrites.
          </p>
        </div>
      )}

      {error && (
        <div className="max-w-xl mx-auto p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-center">
          <p className="text-sm text-rose-300">{error}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 rounded-xl bg-rose-700 hover:bg-rose-600 text-xs font-semibold text-white"
          >
            Retry Evaluation
          </button>
        </div>
      )}

      {!loading && report && <ScorecardView data={report} transcripts={transcripts} />}
    </div>
  );
}
