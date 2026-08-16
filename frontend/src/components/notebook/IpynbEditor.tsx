import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  parseNotebook,
  sourceToString,
  stringifyNotebook,
  stringToSource,
  type NbDocument,
} from "@/lib/ipynb";

type Pyodide = {
  runPythonAsync: (code: string) => Promise<unknown>;
  setStdout: (opts: { batched: (s: string) => void }) => void;
  setStderr: (opts: { batched: (s: string) => void }) => void;
};

const PYODIDE_INDEX =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_PYODIDE_INDEX_URL
    ? String(import.meta.env.VITE_PYODIDE_INDEX_URL)
    : "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/"
  ).replace(/\/?$/, "/");

let pyodidePromise: Promise<Pyodide> | null = null;

function loadPyodideRuntime(): Promise<Pyodide> {
  if (pyodidePromise) return pyodidePromise;
  pyodidePromise = (async () => {
    const w = window as Window & { loadPyodide?: (opts: { indexURL: string }) => Promise<Pyodide> };
    if (!w.loadPyodide) {
      await new Promise<void>((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `${PYODIDE_INDEX}pyodide.js`;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("Pyodide konnte nicht geladen werden"));
        document.head.appendChild(script);
      });
    }
    if (!w.loadPyodide) throw new Error("loadPyodide missing");
    return w.loadPyodide({ indexURL: PYODIDE_INDEX });
  })();
  return pyodidePromise;
}

export function IpynbEditor({
  content,
  onChange,
}: {
  content: string;
  onChange: (next: string) => void;
}) {
  const [nb, setNb] = useState<NbDocument>(() => parseNotebook(content));
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const outputs = useRef<Record<number, string>>({});
  const [, rerender] = useState(0);

  useEffect(() => {
    try {
      setNb(parseNotebook(content));
      setError(null);
    } catch {
      setError("Ungültiges Notebook-JSON");
    }
  }, [content]);

  const commit = useCallback(
    (next: NbDocument) => {
      setNb(next);
      onChange(stringifyNotebook(next));
    },
    [onChange]
  );

  const updateSource = (index: number, text: string) => {
    const next = { ...nb, cells: nb.cells.map((c, i) => (i === index ? { ...c, source: stringToSource(text) } : c)) };
    commit(next);
  };

  const runCell = async (index: number) => {
    const cell = nb.cells[index];
    if (!cell || cell.cell_type !== "code") return;
    setBusy(index);
    setError(null);
    let captured = "";
    try {
      const py = await loadPyodideRuntime();
      py.setStdout({ batched: (s) => { captured += s; } });
      py.setStderr({ batched: (s) => { captured += s; } });
      const result = await py.runPythonAsync(sourceToString(cell.source));
      if (result !== undefined && result !== null && captured === "") {
        captured = String(result);
      }
      outputs.current[index] = captured || "(kein Output)";
    } catch (e) {
      outputs.current[index] = e instanceof Error ? e.message : String(e);
      setError("Zelle fehlgeschlagen (Browser-Kernel, kein Server)");
    } finally {
      setBusy(null);
      rerender((n) => n + 1);
    }
  };

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto">
      <p className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600">
        Läuft im Browser (Pyodide). Keine Datenbank-Credentials im Kernel. BLAST/WES bleiben BRA-APIs.
      </p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {nb.cells.map((cell, index) => (
        <div key={index} className="rounded border border-slate-200 p-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium uppercase text-slate-500">{cell.cell_type}</span>
            {cell.cell_type === "code" && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => void runCell(index)}
                disabled={busy !== null}
              >
                {busy === index ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                <span className="ml-1">Run</span>
              </Button>
            )}
          </div>
          <textarea
            value={sourceToString(cell.source)}
            onChange={(e) => updateSource(index, e.target.value)}
            className="h-28 w-full resize-y rounded border border-slate-200 p-2 font-mono text-sm"
            spellCheck={false}
          />
          {cell.cell_type === "code" && outputs.current[index] && (
            <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-900 p-2 text-xs text-slate-100">
              {outputs.current[index]}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
