"use client";

import React, { useEffect, useRef, useState } from "react";
import { Pen, Square, Circle, ArrowRight, Type, Eraser, Trash2, Camera, Download } from "lucide-react";

interface SystemDesignCanvasProps {
  onSnapshot?: (base64Jpeg: string) => void;
  onWorkingStateChange?: (isActive: boolean) => void;
}

type ToolMode = "pen" | "rect" | "circle" | "arrow" | "text" | "eraser";

export default function SystemDesignCanvas({
  onSnapshot,
  onWorkingStateChange,
}: SystemDesignCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tool, setTool] = useState<ToolMode>("pen");
  const [color, setColor] = useState<string>("#38bdf8"); // Sky blue default
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);

  const snapshotTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const workingStateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize canvas with grid pattern
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Resize canvas to parent container
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Dark grid background
    drawGrid(ctx, rect.width, rect.height);
  }, []);

  const drawGrid = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    ctx.lineWidth = 1;

    const gridSize = 24;
    for (let x = 0; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  };

  const emitSnapshot = () => {
    const canvas = canvasRef.current;
    if (!canvas || !onSnapshot) return;

    // Compress to 50% quality JPEG
    const dataUrl = canvas.toDataURL("image/jpeg", 0.5);
    onSnapshot(dataUrl);
  };

  const scheduleDebouncedSnapshot = () => {
    if (snapshotTimeoutRef.current) {
      clearTimeout(snapshotTimeoutRef.current);
    }
    // Debounce 3 seconds per specification
    snapshotTimeoutRef.current = setTimeout(() => {
      emitSnapshot();
    }, 3000);

    // Working state management
    if (onWorkingStateChange) {
      onWorkingStateChange(true);
      if (workingStateTimeoutRef.current) {
        clearTimeout(workingStateTimeoutRef.current);
      }
      workingStateTimeoutRef.current = setTimeout(() => {
        onWorkingStateChange(false);
      }, 3000);
    }
  };

  const [textInput, setTextInput] = useState("");
  const [textPos, setTextPos] = useState<{ x: number; y: number } | null>(null);
  const [snapshotSent, setSnapshotSent] = useState(false);
  const textInputRef = useRef<HTMLInputElement>(null);

  // Focus input when textPos is set
  useEffect(() => {
    if (textPos && textInputRef.current) {
      textInputRef.current.focus();
    }
  }, [textPos]);

  const commitText = () => {
    if (!textPos || !textInput.trim()) {
      setTextPos(null);
      setTextInput("");
      return;
    }
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.font = "bold 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    const metrics = ctx.measureText(textInput);
    const padding = 6;
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.fillRect(textPos.x - padding, textPos.y - 14 - padding, metrics.width + padding * 2, 20 + padding);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.lineWidth = 1;
    ctx.strokeRect(textPos.x - padding, textPos.y - 14 - padding, metrics.width + padding * 2, 20 + padding);

    ctx.fillStyle = color;
    ctx.fillText(textInput, textPos.x, textPos.y);

    setTextPos(null);
    setTextInput("");
    scheduleDebouncedSnapshot();
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (tool === "text") {
      setTextPos({ x, y });
      return;
    }

    setIsDrawing(true);
    setStartPos({ x, y });

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (tool === "pen") {
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
    } else if (tool === "eraser") {
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.strokeStyle = "#090d16";
      ctx.lineWidth = 24;
      ctx.lineCap = "round";
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (tool === "pen" || tool === "eraser") {
      ctx.lineTo(x, y);
      ctx.stroke();
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    setIsDrawing(false);

    const canvas = canvasRef.current;
    if (!canvas || !startPos) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      if (tool === "rect") {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(startPos.x, startPos.y, x - startPos.x, y - startPos.y);
      } else if (tool === "circle") {
        const radiusX = Math.abs(x - startPos.x) / 2;
        const radiusY = Math.abs(y - startPos.y) / 2;
        const centerX = Math.min(startPos.x, x) + radiusX;
        const centerY = Math.min(startPos.y, y) + radiusY;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
        ctx.stroke();
      } else if (tool === "arrow") {
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(startPos.x, startPos.y);
        ctx.lineTo(x, y);
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(y - startPos.y, x - startPos.x);
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x - 12 * Math.cos(angle - Math.PI / 6), y - 12 * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(x - 12 * Math.cos(angle + Math.PI / 6), y - 12 * Math.sin(angle + Math.PI / 6));
        ctx.fill();
      }
    }

    setStartPos(null);
    scheduleDebouncedSnapshot();
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    drawGrid(ctx, rect.width, rect.height);
    scheduleDebouncedSnapshot();
  };

  const handleDownload = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = "system-design-architecture.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  const handleSnapshotManual = () => {
    emitSnapshot();
    setSnapshotSent(true);
    setTimeout(() => setSnapshotSent(false), 2000);
  };

  return (
    <div className="flex flex-col h-full rounded-2xl glass-panel border border-slate-800 bg-slate-900/95 overflow-hidden shadow-2xl">
      {/* Canvas Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800">
        {/* Drawing Tools */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setTool("pen")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "pen"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Pen (Freehand)"
          >
            <Pen className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setTool("rect")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "rect"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Rectangle (Architecture Component)"
          >
            <Square className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setTool("circle")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "circle"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Circle (Database / Storage)"
          >
            <Circle className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setTool("arrow")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "arrow"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Arrow (Data Flow)"
          >
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setTool("text")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "text"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Text Label (Click canvas to place)"
          >
            <Type className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => setTool("eraser")}
            className={`p-2 rounded-lg text-xs font-medium transition-colors ${
              tool === "eraser"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
            title="Eraser"
          >
            <Eraser className="w-4 h-4" />
          </button>
        </div>

        {/* Color Palette & Actions */}
        <div className="flex items-center gap-2">
          {["#38bdf8", "#34d399", "#fbbf24", "#f43f5e", "#c084fc", "#ffffff"].map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              className={`w-5 h-5 rounded-full border-2 transition-transform ${
                color === c ? "scale-125 border-white" : "border-transparent opacity-75 hover:opacity-100"
              }`}
              style={{ backgroundColor: c }}
            />
          ))}

          <div className="h-4 w-px bg-slate-800 mx-1" />

          {snapshotSent && (
            <span className="text-[11px] text-emerald-400 font-medium px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/40 animate-pulse">
              AI Synced
            </span>
          )}

          <button
            type="button"
            onClick={clearCanvas}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-rose-900/40 hover:text-rose-300 transition-colors"
            title="Clear Canvas"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={handleDownload}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            title="Download Diagram (PNG)"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={handleSnapshotManual}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-blue-600 hover:text-white transition-colors flex items-center gap-1 text-xs"
            title="Send Diagram Snapshot to AI"
          >
            <Camera className="w-4 h-4" />
            <span className="hidden sm:inline">Sync AI</span>
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 relative cursor-crosshair overflow-hidden">
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className="w-full h-full block"
        />

        {/* Inline Text Input Overlay when Text Tool is active and user clicked */}
        {textPos && (
          <div
            className="absolute z-20 flex items-center gap-1.5 bg-slate-900 border border-blue-500 rounded-lg p-1.5 shadow-xl"
            style={{
              left: Math.min(textPos.x, (canvasRef.current?.clientWidth || 400) - 180),
              top: Math.max(10, textPos.y - 20),
            }}
          >
            <input
              ref={textInputRef}
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitText();
                if (e.key === "Escape") {
                  setTextPos(null);
                  setTextInput("");
                }
              }}
              placeholder="Label (e.g. Kafka, Redis)..."
              className="bg-slate-950 text-white text-xs px-2 py-1 rounded outline-none border border-slate-700 w-36"
            />
            <button
              type="button"
              onClick={commitText}
              className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded transition-colors"
            >
              Add
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
