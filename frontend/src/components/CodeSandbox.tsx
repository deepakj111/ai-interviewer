"use client";

import React, { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { Play, RotateCcw, CheckCircle, XCircle, Clock, Table, Terminal } from "lucide-react";
import { executePythonCode, PythonExecutionResult } from "@/lib/pyodideRunner";
import { executeSQLQuery, SQLQueryResult } from "@/lib/duckdbRunner";

interface CodeSandboxProps {
  initialLanguage?: "python" | "sql";
  initialCode?: string;
  seedSql?: string;
  unitTests?: string;
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
  onCodeExecuted,
  onWorkingStateChange,
}: CodeSandboxProps) {
  const [language, setLanguage] = useState<"python" | "sql">(initialLanguage);
  const [code, setCode] = useState(initialCode);
  const [isRunning, setIsRunning] = useState(false);
  const [pythonResult, setPythonResult] = useState<PythonExecutionResult | null>(null);
  const [sqlResult, setSqlResult] = useState<SQLQueryResult | null>(null);
  const [activeConsoleTab, setActiveConsoleTab] = useState<"stdout" | "table">("stdout");

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

  return (
    <div className="flex flex-col h-full rounded-2xl glass-panel border border-slate-800 bg-slate-900/95 overflow-hidden shadow-2xl">
      {/* Editor Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800">
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
      <div className="flex-1 min-h-[300px]">
        <Editor
          height="100%"
          language={language === "python" ? "python" : "sql"}
          theme="vs-dark"
          value={code}
          onChange={handleEditorChange}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            padding: { top: 12, bottom: 12 },
          }}
        />
      </div>

      {/* Output Console / Tabular Results */}
      <div className="h-[220px] border-t border-slate-800 bg-slate-950 flex flex-col">
        {/* Console Tabs */}
        <div className="flex items-center justify-between px-4 py-1.5 border-b border-slate-800/80 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setActiveConsoleTab("stdout")}
              className={`text-xs flex items-center gap-1.5 py-1 font-medium transition-colors ${
                activeConsoleTab === "stdout"
                  ? "text-blue-400 border-b-2 border-blue-500"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" /> Output
            </button>

            {sqlResult && (
              <button
                type="button"
                onClick={() => setActiveConsoleTab("table")}
                className={`text-xs flex items-center gap-1.5 py-1 font-medium transition-colors ${
                  activeConsoleTab === "table"
                    ? "text-blue-400 border-b-2 border-blue-500"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Table className="w-3.5 h-3.5" /> Result Set ({sqlResult.rowCount})
              </button>
            )}
          </div>

          {/* Timing & Status */}
          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            {pythonResult && (
              <>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {pythonResult.executionTimeMs}ms
                </span>
                {pythonResult.testPassed ? (
                  <span className="flex items-center gap-1 text-emerald-400 font-medium">
                    <CheckCircle className="w-3.5 h-3.5" /> Tests Passed
                  </span>
                ) : pythonResult.error ? (
                  <span className="flex items-center gap-1 text-rose-400 font-medium">
                    <XCircle className="w-3.5 h-3.5" /> Execution Error
                  </span>
                ) : null}
              </>
            )}

            {sqlResult && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                {sqlResult.executionTimeMs}ms
              </span>
            )}
          </div>
        </div>

        {/* Console Body */}
        <div className="flex-1 p-3 overflow-auto font-mono text-xs">
          {activeConsoleTab === "stdout" && (
            <div>
              {pythonResult?.stdout && (
                <pre className="text-slate-200 whitespace-pre-wrap">{pythonResult.stdout}</pre>
              )}
              {pythonResult?.error && (
                <pre className="text-rose-400 whitespace-pre-wrap mt-1">
                  {pythonResult.error}
                </pre>
              )}
              {sqlResult && !pythonResult && (
                <p className="text-slate-400">
                  Query returned {sqlResult.rowCount} rows in {sqlResult.executionTimeMs}ms. See Result Set tab.
                </p>
              )}
              {!pythonResult && !sqlResult && !isRunning && (
                <span className="text-slate-600">Console output will appear here after running code...</span>
              )}
            </div>
          )}

          {activeConsoleTab === "table" && sqlResult && (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/80">
                    {sqlResult.columns.map((col, idx) => (
                      <th key={idx} className="p-2 font-semibold text-slate-300">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sqlResult.rows.map((row, rowIdx) => (
                    <tr
                      key={rowIdx}
                      className="border-b border-slate-900/50 hover:bg-slate-900/30 transition-colors"
                    >
                      {row.map((cell, cellIdx) => (
                        <td key={cellIdx} className="p-2 text-slate-300">
                          {cell === null ? (
                            <span className="text-slate-600 italic">null</span>
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
