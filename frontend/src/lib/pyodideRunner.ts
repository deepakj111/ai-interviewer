/**
 * Client-Side Pyodide WebAssembly runner for zero-server Python execution.
 */

declare global {
  interface Window {
    loadPyodide?: any;
    pyodide?: any;
  }
}

let pyodideInstance: any = null;
let pyodideLoadPromise: Promise<any> | null = null;

export async function getPyodideInstance(): Promise<any> {
  if (pyodideInstance) {
    return pyodideInstance;
  }
  if (pyodideLoadPromise) {
    return pyodideLoadPromise;
  }

  pyodideLoadPromise = new Promise(async (resolve, reject) => {
    try {
      if (typeof window === "undefined") {
        return reject(new Error("Pyodide can only run in browser"));
      }

      // Check if pyodide script already in document
      if (!window.loadPyodide) {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
        script.async = true;
        document.head.appendChild(script);

        await new Promise((res, rej) => {
          script.onload = res;
          script.onerror = () => rej(new Error("Failed to load Pyodide from CDN"));
        });
      }

      const pyodide = await window.loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/",
      });

      // Pre-load common scientific packages (numpy)
      try {
        await pyodide.loadPackage(["numpy"]);
      } catch (e) {
        console.warn("Could not preload numpy in Pyodide:", e);
      }

      pyodideInstance = pyodide;
      resolve(pyodide);
    } catch (err) {
      reject(err);
    }
  });

  return pyodideLoadPromise;
}

export interface PythonExecutionResult {
  stdout: string;
  stderr: string;
  error?: string;
  executionTimeMs: number;
  testPassed?: boolean;
}

export async function executePythonCode(
  code: string,
  unitTests?: string
): Promise<PythonExecutionResult> {
  const startTime = performance.now();
  try {
    const pyodide = await getPyodideInstance();

    // Prepare wrapper that intercepts stdout & stderr
    const fullCode = `
import sys
import io

_stdout_buf = io.StringIO()
_stderr_buf = io.StringIO()
_orig_stdout = sys.stdout
_orig_stderr = sys.stderr
sys.stdout = _stdout_buf
sys.stderr = _stderr_buf

_test_passed = True
try:
${code.split("\n").map((line) => "    " + line).join("\n")}

${unitTests ? unitTests.split("\n").map((line) => "    " + line).join("\n") : ""}
except Exception as e:
    _test_passed = False
    import traceback
    traceback.print_exc(file=_stderr_buf)
finally:
    sys.stdout = _orig_stdout
    sys.stderr = _orig_stderr

_captured_stdout = _stdout_buf.getvalue()
_captured_stderr = _stderr_buf.getvalue()
`;

    await pyodide.runPythonAsync(fullCode);

    const stdout = pyodide.globals.get("_captured_stdout") || "";
    const stderr = pyodide.globals.get("_captured_stderr") || "";
    const testPassed = pyodide.globals.get("_test_passed");
    const executionTimeMs = Math.round(performance.now() - startTime);

    return {
      stdout,
      stderr,
      executionTimeMs,
      testPassed: Boolean(testPassed && !stderr),
      error: stderr ? stderr : undefined,
    };
  } catch (err: any) {
    const executionTimeMs = Math.round(performance.now() - startTime);
    return {
      stdout: "",
      stderr: err.message || String(err),
      error: err.message || String(err),
      executionTimeMs,
      testPassed: false,
    };
  }
}
