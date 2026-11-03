/**
 * Centralized API configuration & dynamic backend URL detection.
 * Supports local dev, custom ports, reverse proxies, and Docker environments.
 */

export function getBackendBaseUrl(): string {
  if (typeof window !== "undefined") {
    // If explicit env var is set
    if (process.env.NEXT_PUBLIC_BACKEND_URL) {
      return process.env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "");
    }
    // Default to port 8000 on the current browser hostname
    const host = window.location.hostname || "localhost";
    return `http://${host}:8000`;
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
}

export function getWebSocketBaseUrl(): string {
  if (typeof window !== "undefined") {
    if (process.env.NEXT_PUBLIC_WS_URL) {
      return process.env.NEXT_PUBLIC_WS_URL.replace(/\/$/, "");
    }
    const host = window.location.hostname || "localhost";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${host}:8000`;
  }
  return "ws://localhost:8000";
}

export function getApiUrl(path: string): string {
  const base = getBackendBaseUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export function getWsUrl(path: string): string {
  const base = getWebSocketBaseUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export async function checkBackendHealth(): Promise<{
  ok: boolean;
  latencyMs: number;
  statusText: string;
}> {
  const start = performance.now();
  try {
    const res = await fetch(getApiUrl("/api/health"), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(4000),
    });
    const latencyMs = Math.round(performance.now() - start);
    if (res.ok) {
      return { ok: true, latencyMs, statusText: "Connected (Healthy)" };
    }
    return { ok: false, latencyMs, statusText: `HTTP ${res.status}` };
  } catch (err: any) {
    const latencyMs = Math.round(performance.now() - start);
    return {
      ok: false,
      latencyMs,
      statusText: err.name === "TimeoutError" ? "Timeout" : "Offline / Unreachable",
    };
  }
}
