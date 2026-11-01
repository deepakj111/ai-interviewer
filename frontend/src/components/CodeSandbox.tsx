"use client";

import React, { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import {
  Play,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  Table,
  Terminal,
  ChevronDown,
  ChevronUp,
  Database,
  HelpCircle,
  Lightbulb,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { executePythonCode, PythonExecutionResult } from "@/lib/pyodideRunner";
import { executeSQLQuery, SQLQueryResult } from "@/lib/duckdbRunner";

interface CodeSandboxProps {
  initialLanguage?: "python" | "sql";
  initialCode?: string;
  seedSql?: string;
  unitTests?: string;
  activeQuestion?: any;
  onAskInterviewer?: (prompt: string) => void;
  onCodeExecuted?: (payload: {
    language: string;
    code: string;
    stdout: string;
    error?: string;
  }) => void;
  onWorkingStateChange?: (isActive: boolean) => void;
}

export default function CodeSandbox({
  initialLanguage = "python",
  initialCode = "",
  seedSql,
  unitTests,
  activeQuestion,
  onAskInterviewer,
  onCodeExecuted,
  onWorkingStateChange,
}: CodeSandboxProps) {
  const [language, setLanguage] = useState<"python" | "sql">(initialLanguage);
  const [code, setCode] = useState(initialCode);
  const [isRunning, setIsRunning] = useState(false);
  const [pythonResult, setPythonResult] = useState<PythonExecutionResult | null>(null);
  const [sqlResult, setSqlResult] = useState<SQLQueryResult | null>(null);
  const [activeConsoleTab, setActiveConsoleTab] = useState<"stdout" | "table">("stdout");
  const [isProblemExpanded, setIsProblemExpanded] = useState(true);
  const [isSchemaVisible, setIsSchemaVisible] = useState(false);

  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Sync initial code when prop changes
  useEffect(() => {
    if (initialCode) {
      setCode(initialCode);
    }
  }, [initialCode]);

  useEffect(() => {
    if (initialLanguage) {
      setLanguage(initialLanguage);
      if (initialLanguage === "sql") {
        setActiveConsoleTab("table");
      } else {
        setActiveConsoleTab("stdout");
      }
    }
  }, [initialLanguage]);

  // Keystroke VAD gate: emit active working state when candidate types
  const handleEditorChange = (value: string | undefined) => {
    setCode(value || "");

    if (onWorkingStateChange) {
      onWorkingStateChange(true);

      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
      }
      // Revert working state after 2.5 seconds of inactivity
      typingTimerRef.current = setTimeout(() => {
        onWorkingStateChange(false);
      }, 2500);
    }
  };

  const handleRun = async () => {
    setIsRunning(true);
    setPythonResult(null);
    setSqlResult(null);

    try {
      if (language === "python") {
        const res = await executePythonCode(code, unitTests);
        setPythonResult(res);
        setActiveConsoleTab("stdout");

        if (onCodeExecuted) {
          onCodeExecuted({
            language: "python",
            code,
            stdout: res.stdout,
            error: res.error,
          });
        }
      } else {
        const res = await executeSQLQuery(code, seedSql);
        setSqlResult(res);
        setActiveConsoleTab("table");

        if (onCodeExecuted) {
          onCodeExecuted({
            language: "sql",
            code,
            stdout: `Query executed in ${res.executionTimeMs}ms (${res.rowCount} rows returned)`,
          });
        }
      }
    } catch (err: any) {
      console.error("Execution error:", err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleResetCode = () => {
    if (initialCode) {
      setCode(initialCode);
    }
  };

  return (
    <div className="flex flex-col h-full rounded-2xl glass-panel border border-slate-800 bg-slate-900/95 overflow-hidden shadow-2xl">
      {/* Active Problem & Reference Schema Banner */}
      {activeQuestion && (
        <div className="bg-slate-950/90 border-b border-slate-800/80 px-4 py-2.5 transition-all">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-bold uppercase tracking-wider">
                {activeQuestion.category || language.toUpperCase()}
              </span>
              <span className="text-xs font-bold text-white tracking-tight">
                {activeQuestion.title || "Live Coding Problem"}
              </span>
              <span className="text-[10px] text-slate-400">
                ({activeQuestion.difficulty || "Senior"})
              </span>
            </div>

            <div className="flex items-center gap-2">
              {language === "sql" && seedSql && (
                <button
                  type="button"
                  onClick={() => setIsSchemaVisible(!isSchemaVisible)}
                  className={`px-2 py-1 rounded-md text-[11px] font-medium flex items-center gap-1 border transition-colors ${
                    isSchemaVisible
                      ? "bg-blue-600/20 border-blue-500/50 text-blue-300"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                  title="View seeded table schemas and sample data"
                >
                  <Database className="w-3 h-3 text-blue-400" />
                  <span>{isSchemaVisible ? "Hide Schema" : "View Schema"}</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsProblemExpanded(!isProblemExpanded)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-md transition-colors"
                title={isProblemExpanded ? "Collapse prompt" : "Expand prompt"}
              >
                {isProblemExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {isProblemExpanded && (
            <div className="mt-2 space-y-2">
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/60 whitespace-pre-wrap">
                {activeQuestion.prompt}
              </p>

              {/* Quick AI Probing Action Chips */}
              {onAskInterviewer && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] text-slate-500 font-medium mr-1">Ask AI:</span>
                  <button
                    type="button"
                    onClick={() => onAskInterviewer("Can you explain the question and what you're looking for?")}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1 transition-colors"
                  >
                    <MessageSquare className="w-3 h-3 text-blue-400" /> Explain Problem
                  </button>
                  <button
                    type="button"
                    onClick={() => onAskInterviewer("Could you clarify the table schema, data types, and scale constraints?")}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1 transition-colors"
                  >
                    <HelpCircle className="w-3 h-3 text-emerald-400" /> Clarify Constraints
                  </button>
                  <button
                    type="button"
                    onClick={() => onAskInterviewer("I'm thinking about the approach, can you give me a progressive hint?")}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1 transition-colors"
                  >
                    <Lightbulb className="w-3 h-3 text-amber-400" /> Request Hint
                  </button>
                  <button
                    type="button"
                    onClick={() => onAskInterviewer("What Big-O runtime and memory space complexity are you aiming for?")}
                    className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1 transition-colors"
                  >
                    <Sparkles className="w-3 h-3 text-purple-400" /> Complexity Target
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Seed Schema Preview Panel */}
          {isSchemaVisible && seedSql && (
            <div className="mt-2 p-2.5 bg-slate-900/95 border border-blue-500/30 rounded-xl max-h-36 overflow-y-auto">
              <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-semibold text-blue-400">
                <Database className="w-3 h-3" /> Pre-Seeded DuckDB Tables
              </div>
              <pre className="text-[10px] text-slate-300 font-mono leading-relaxed overflow-x-auto">
                {seedSql.trim()}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Editor Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800">
        <div className="flex items-center gap-2">
          {/* Language Switcher */}
          <div className="flex bg-slate-900 rounded-lg p-0.5 border border-slate-800 text-xs font-medium">
            <button
              type="button"
              onClick={() => {
                setLanguage("python");
                setActiveConsoleTab("stdout");
              }}
              className={`px-3 py-1 rounded-md transition-colors ${
                language === "python"
                  ? "bg-blue-600 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Python (WASM)
            </button>
            <button
              type="button"
              onClick={() => {
                setLanguage("sql");
                setActiveConsoleTab("table");
              }}
              className={`px-3 py-1 rounded-md transition-colors ${
                language === "sql"
                  ? "bg-blue-600 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              SQL (DuckDB)
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetCode}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800 text-xs transition-colors"
            title="Reset to starter code"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md ${
              isRunning
                ? "bg-blue-800 text-slate-300 cursor-not-allowed"
                : "bg-emerald-600 hover:bg-emerald-500 text-white hover:shadow-emerald-600/30"
            }`}
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isRunning ? "animate-spin" : ""}`} />
            {isRunning ? "Running..." : language === "python" ? "Run Code" : "Run Query"}
          </button>
        </div>
      </div>

      {/* Monaco Code Editor */}
      <div className="flex-1 min-h-[260px]">
        <Editor
          height="100%"
          language={language === "python" ? "python" : "sql"}
          theme="vs-dark"
          value={code}
          onChange={handleEditorChange}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            tabSize: 4,
            padding: { top: 12 },
          }}
        />
      </div>

      {/* Output Console / Table Result */}
      <div className="h-44 border-t border-slate-800 bg-slate-950 flex flex-col">
        {/* Console Header */}
        <div className="flex items-center justify-between px-4 py-1.5 bg-slate-900 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveConsoleTab("stdout")}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold flex items-center gap-1.5 transition-colors ${
                activeConsoleTab === "stdout"
                  ? "bg-slate-800 text-slate-200"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Terminal className="w-3 h-3" /> Console Output
            </button>

            {language === "sql" && (
              <button
                type="button"
                onClick={() => setActiveConsoleTab("table")}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold flex items-center gap-1.5 transition-colors ${
                  activeConsoleTab === "table"
                    ? "bg-slate-800 text-slate-200"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Table className="w-3 h-3" /> Result Table
              </button>
            )}
          </div>

          {/* Execution Time badge */}
          {(pythonResult || sqlResult) && (
            <div className="flex items-center gap-1 text-[10px] text-slate-400">
              <Clock className="w-3 h-3 text-blue-400" />
              <span>
                {language === "python"
                  ? `${pythonResult?.executionTimeMs}ms`
                  : `${sqlResult?.executionTimeMs}ms`}
              </span>
            </div>
          )}
        </div>

        {/* Console Content */}
        <div className="flex-1 p-3 overflow-auto font-mono text-xs">
          {activeConsoleTab === "stdout" && (
            <div>
              {pythonResult?.stdout && (
                <pre className="text-slate-200 whitespace-pre-wrap">{pythonResult.stdout}</pre>
              )}
              {pythonResult?.error && (
                <div className="text-rose-400 flex items-start gap-1.5 mt-1 bg-rose-950/20 p-2 rounded border border-rose-800/40">
                  <XCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <pre className="whitespace-pre-wrap">{pythonResult.error}</pre>
                </div>
              )}
              {pythonResult?.testPassed && (
                <div className="text-emerald-400 flex items-center gap-1.5 mt-2 bg-emerald-950/20 p-1.5 rounded border border-emerald-800/40">
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>All unit tests passed!</span>
                </div>
              )}
              {language === "sql" && sqlResult && (
                <p className="text-slate-300">
                  Query returned {sqlResult.rowCount} rows in {sqlResult.executionTimeMs}ms.
                </p>
              )}
              {!pythonResult && !sqlResult && (
                <p className="text-slate-500 italic">
                  Press &apos;{language === "python" ? "Run Code" : "Run Query"}&apos; to execute your solution in-browser (WASM).
                </p>
              )}
            </div>
          )}

          {activeConsoleTab === "table" && sqlResult && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse border border-slate-800">
                <thead>
                  <tr className="bg-slate-900 text-slate-300 text-[11px]">
                    {sqlResult.columns.map((col, idx) => (
                      <th key={idx} className="p-2 border border-slate-800 font-semibold">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sqlResult.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-900/50 border-b border-slate-800/60">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="p-2 border border-slate-800 text-slate-200">
                          {cell === null ? (
                            <span className="text-slate-500 italic">NULL</span>
                          ) : (
                            String(cell)
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
