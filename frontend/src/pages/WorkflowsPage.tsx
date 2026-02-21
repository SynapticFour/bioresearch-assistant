import { useState, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Settings, Play, ExternalLink, BadgeCheck } from "lucide-react";
import {
  wes,
  type WesRunSummary,
  type WesRunLog,
} from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const REFETCH_INTERVAL_MS = 10_000;

type WorkflowKind = "blast" | "star" | "gatk" | "custom";

const WORKFLOW_OPTIONS: { value: WorkflowKind; label: string }[] = [
  { value: "blast", label: "BLAST Suche" },
  { value: "star", label: "RNA-Seq Alignment (STAR)" },
  { value: "gatk", label: "Variant Calling (GATK)" },
  { value: "custom", label: "Custom Nextflow Workflow" },
];

// Placeholder workflow URLs (replace with real paths/URLs in deployment)
const WORKFLOW_URLS: Record<WorkflowKind, string> = {
  blast: "https://github.com/nf-core/blast/raw/master/main.nf",
  star: "https://github.com/nf-core/rnaseq/raw/master/main.nf",
  gatk: "https://github.com/nf-core/sarek/raw/master/main.nf",
  custom: "",
};

function statusBadgeClass(state: string): string {
  const s = (state || "").toUpperCase();
  if (s === "QUEUED" || s === "INITIALIZING" || s === "CANCELING")
    return "bg-slate-100 text-slate-700 border-slate-200";
  if (s === "RUNNING") return "bg-amber-100 text-amber-800 border-amber-200";
  if (s === "COMPLETE") return "bg-green-100 text-green-800 border-green-200";
  if (s === "FAILED" || s === "EXECUTOR_ERROR" || s === "SYSTEM_ERROR")
    return "bg-red-100 text-red-800 border-red-200";
  if (s === "CANCELED" || s === "PREEMPTED")
    return "bg-orange-100 text-orange-800 border-orange-200";
  return "bg-slate-100 text-slate-600 border-slate-200";
}

function isRunningOrQueued(state: string): boolean {
  const s = (state || "").toUpperCase();
  return s === "RUNNING" || s === "QUEUED" || s === "INITIALIZING" || s === "CANCELING";
}

function formatTime(iso: string | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function formatDuration(
  start: string | undefined,
  end: string | undefined
): string {
  if (!start) return "—";
  const startMs = new Date(start).getTime();
  const endMs = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((endMs - startMs) / 1000);
  if (sec < 60) return `${sec} s`;
  const min = Math.floor(sec / 60);
  const s = sec % 60;
  if (min < 60) return `${min} min ${s} s`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h} h ${m} min`;
}

// --- Start Pipeline Panel ---

interface StartPanelProps {
  workflow: WorkflowKind;
  setWorkflow: (w: WorkflowKind) => void;
  blastQuery: string;
  setBlastQuery: (s: string) => void;
  blastDatabase: string;
  setBlastDatabase: (s: string) => void;
  blastEvalue: string;
  setBlastEvalue: (s: string) => void;
  starFastqFiles: File[];
  setStarFastqFiles: (f: File[]) => void;
  starReference: string;
  setStarReference: (s: string) => void;
  customUrl: string;
  setCustomUrl: (s: string) => void;
  customParamsJson: string;
  setCustomParamsJson: (s: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}

function StartPanel({
  workflow,
  setWorkflow,
  blastQuery,
  setBlastQuery,
  blastDatabase,
  setBlastDatabase,
  blastEvalue,
  setBlastEvalue,
  starFastqFiles,
  setStarFastqFiles,
  starReference,
  setStarReference,
  customUrl,
  setCustomUrl,
  customParamsJson,
  setCustomParamsJson,
  onSubmit,
  isSubmitting,
}: StartPanelProps) {
  const [paramError, setParamError] = useState<string | null>(null);

  const handleSubmit = useCallback(() => {
    if (workflow === "custom") {
      try {
        JSON.parse(customParamsJson || "{}");
      } catch {
        setParamError("Ungültiges JSON");
        return;
      }
    }
    setParamError(null);
    onSubmit();
  }, [workflow, customParamsJson, onSubmit]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-slate-800">
        <Play className="h-5 w-5" />
        Workflow starten
      </h2>
      <div className="mb-4">
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Workflow
        </label>
        <select
          value={workflow}
          onChange={(e) => setWorkflow(e.target.value as WorkflowKind)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          {WORKFLOW_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {workflow === "blast" && (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Query Sequence
            </label>
            <textarea
              value={blastQuery}
              onChange={(e) => setBlastQuery(e.target.value)}
              placeholder="ATCG..."
              rows={4}
              className="w-full rounded-lg border border-slate-300 p-3 font-mono text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Datenbank
            </label>
            <select
              value={blastDatabase}
              onChange={(e) => setBlastDatabase(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="nr">nr</option>
              <option value="nt">nt</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              E-Value
            </label>
            <input
              type="number"
              step="any"
              min="0"
              value={blastEvalue}
              onChange={(e) => setBlastEvalue(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
      )}

      {workflow === "star" && (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              FASTQ Dateien
            </label>
            <input
              type="file"
              multiple
              accept=".fastq,.fq,.fastq.gz,.fq.gz"
              onChange={(e) => setStarFastqFiles(Array.from(e.target.files ?? []))}
              className="w-full text-sm text-slate-600 file:mr-2 file:rounded file:border-0 file:bg-primary file:px-4 file:py-2 file:text-primary-foreground"
            />
            {starFastqFiles.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                {starFastqFiles.length} Datei(en) ausgewählt
              </p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Referenz-Genom
            </label>
            <select
              value={starReference}
              onChange={(e) => setStarReference(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="GRCh38">GRCh38</option>
              <option value="GRCm39">GRCm39</option>
              <option value="custom">Custom</option>
            </select>
          </div>
        </div>
      )}

      {workflow === "gatk" && (
        <p className="text-sm text-slate-500">
          Parameter für GATK (Sarek) — nutze Custom Workflow für volle Kontrolle.
        </p>
      )}

      {workflow === "custom" && (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Workflow URL
            </label>
            <input
              type="url"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              placeholder="https://..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Parameter (JSON)
            </label>
            <textarea
              value={customParamsJson}
              onChange={(e) => setCustomParamsJson(e.target.value)}
              placeholder='{"param1": "value1"}'
              rows={6}
              className="w-full rounded-lg border border-slate-300 p-3 font-mono text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            {paramError && (
              <p className="mt-1 text-sm text-red-600">{paramError}</p>
            )}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button
          onClick={handleSubmit}
          disabled={
            isSubmitting ||
            (workflow === "custom" && !customUrl.trim())
          }
        >
          {isSubmitting ? "Wird gestartet…" : "Pipeline starten"}
        </Button>
        <Badge variant="outline" className="gap-1 text-xs">
          <BadgeCheck className="h-3.5 w-3.5" />
          WES v1.1 kompatibel
        </Badge>
      </div>
    </section>
  );
}

// --- Runs table ---

interface RunsTableProps {
  runs: WesRunSummary[];
  isLoading: boolean;
  onDetails: (run: WesRunSummary) => void;
  onCancel: (run: WesRunSummary) => void;
  onLogs: (run: WesRunSummary) => void;
}

function RunsTable({
  runs,
  isLoading,
  onDetails,
  onCancel,
  onLogs,
}: RunsTableProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 p-4">
        <h2 className="text-lg font-semibold text-slate-800">Pipeline Runs</h2>
      </div>
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="p-8">
            <div className="h-32 animate-pulse rounded bg-slate-100" />
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-4 py-3 font-medium">Run ID</th>
                <th className="px-4 py-3 font-medium">Workflow</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Gestartet</th>
                <th className="px-4 py-3 font-medium">Dauer</th>
                <th className="px-4 py-3 font-medium">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Noch keine Runs
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr
                    key={run.run_id}
                    className="border-b border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-4 py-2 font-mono text-xs">
                      {run.run_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-2 text-slate-700">
                      {run.workflow_url
                        ? run.workflow_url.split("/").pop() ?? run.workflow_url
                        : "—"}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={cn(
                          "inline-flex rounded border px-2 py-0.5 text-xs font-medium",
                          statusBadgeClass(run.state),
                          (run.state || "").toUpperCase() === "RUNNING" &&
                            "animate-pulse"
                        )}
                      >
                        {run.state}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-600">
                      {formatTime(
                        (run.run_log as { start_time?: string } | undefined)
                          ?.start_time
                      )}
                    </td>
                    <td className="px-4 py-2 text-slate-600">
                      {formatDuration(
                        (run.run_log as { start_time?: string } | undefined)
                          ?.start_time,
                        (run.run_log as { end_time?: string } | undefined)
                          ?.end_time
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDetails(run)}
                        >
                          Details
                        </Button>
                        {isRunningOrQueued(run.state) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onCancel(run)}
                            className="text-amber-700"
                          >
                            Abbrechen
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onLogs(run)}
                        >
                          Logs
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// --- Run Detail Modal ---

interface RunDetailModalProps {
  run: WesRunLog | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function RunDetailModal({ run, open, onOpenChange }: RunDetailModalProps) {
  if (!run) return null;
  const req = run.request;
  const log = run.run_log;
  const start = log?.start_time;
  const end = log?.end_time;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-mono text-base">
            {run.run_id}
            <span
              className={cn(
                "rounded border px-2 py-0.5 text-xs font-medium",
                statusBadgeClass(run.state)
              )}
            >
              {run.state}
            </span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          {req && (
            <>
              <div>
                <h4 className="font-medium text-slate-700">Workflow URL</h4>
                <p className="mt-1 break-all font-mono text-xs text-slate-600">
                  {req.workflow_url}
                </p>
              </div>
              {req.workflow_params && Object.keys(req.workflow_params).length > 0 && (
                <div>
                  <h4 className="font-medium text-slate-700">Parameter</h4>
                  <pre className="mt-1 max-h-40 overflow-auto rounded bg-slate-100 p-2 text-xs">
                    {JSON.stringify(req.workflow_params, null, 2)}
                  </pre>
                </div>
              )}
            </>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-slate-500">Start</span>
              <p className="font-medium">{formatTime(start)}</p>
            </div>
            <div>
              <span className="text-slate-500">Ende</span>
              <p className="font-medium">{formatTime(end)}</p>
            </div>
            <div>
              <span className="text-slate-500">Dauer</span>
              <p className="font-medium">{formatDuration(start, end)}</p>
            </div>
          </div>
          {run.outputs && Object.keys(run.outputs).length > 0 && (
            <div>
              <h4 className="font-medium text-slate-700">Outputs (DRS)</h4>
              <ul className="mt-1 list-inside list-disc text-slate-600">
                {Object.entries(run.outputs).map(([k, v]) => (
                  <li key={k}>
                    {k}:{" "}
                    {typeof v === "string" && v.startsWith("drs://") ? (
                      <a
                        href={v}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {v}
                        <ExternalLink className="ml-1 inline h-3 w-3" />
                      </a>
                    ) : (
                      String(v)
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {(log?.stdout || log?.stderr) && (
            <div>
              <h4 className="font-medium text-slate-700">Log</h4>
              <pre className="mt-1 max-h-[400px] overflow-auto rounded border border-slate-200 bg-slate-50 p-3 font-mono text-xs">
                {log.stdout && `--- stdout ---\n${log.stdout}\n`}
                {log.stderr && `--- stderr ---\n${log.stderr}`}
              </pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// --- Logs Modal ---

interface LogsModalProps {
  runId: string;
  stdout: string;
  stderr: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function LogsModal({
  runId,
  stdout,
  stderr,
  open,
  onOpenChange,
}: LogsModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">Logs — {runId}</DialogTitle>
        </DialogHeader>
        <pre className="max-h-[400px] overflow-auto rounded border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-100">
          {stdout && `--- stdout ---\n${stdout}\n`}
          {stderr && `--- stderr ---\n${stderr}`}
          {!stdout && !stderr && "Keine Logs vorhanden."}
        </pre>
      </DialogContent>
    </Dialog>
  );
}

// --- Main page ---

export function WorkflowsPage() {
  const queryClient = useQueryClient();
  const [workflow, setWorkflow] = useState<WorkflowKind>("blast");
  const [blastQuery, setBlastQuery] = useState("");
  const [blastDatabase, setBlastDatabase] = useState("nt");
  const [blastEvalue, setBlastEvalue] = useState("10");
  const [starFastqFiles, setStarFastqFiles] = useState<File[]>([]);
  const [starReference, setStarReference] = useState("GRCh38");
  const [customUrl, setCustomUrl] = useState("");
  const [customParamsJson, setCustomParamsJson] = useState("{}");
  const [detailRun, setDetailRun] = useState<WesRunSummary | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [logsRunId, setLogsRunId] = useState<string | null>(null);
  const [logsContent, setLogsContent] = useState({ stdout: "", stderr: "" });
  const [logsOpen, setLogsOpen] = useState(false);

  const runsQuery = useQuery({
    queryKey: ["wes-runs"],
    queryFn: () => wes.listRuns({ page_size: 100 }),
    refetchInterval: (query) => {
      const runs = (query.state.data as { runs: WesRunSummary[] } | undefined)
        ?.runs;
      const hasRunning = runs?.some((r) =>
        isRunningOrQueued((r.state || "").toUpperCase())
      );
      return hasRunning ? REFETCH_INTERVAL_MS : false;
    },
  });

  const runs = runsQuery.data?.runs ?? [];

  const submitMutation = useMutation({
    mutationFn: async () => {
      let url: string;
      let params: Record<string, unknown> = {};
      let attachments: File[] | undefined;

      if (workflow === "custom") {
        url = customUrl.trim();
        try {
          params = JSON.parse(customParamsJson || "{}");
        } catch {
          throw new Error("Ungültiges JSON");
        }
      } else {
        url = WORKFLOW_URLS[workflow];
        if (workflow === "blast") {
          params = {
            query: blastQuery.trim(),
            database: blastDatabase,
            evalue: parseFloat(blastEvalue) || 10,
          };
        }
        if (workflow === "star") {
          params = { reference: starReference };
          attachments = starFastqFiles.length > 0 ? starFastqFiles : undefined;
        }
      }
      return wes.submitRun(url, params, attachments);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["wes-runs"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: string) => wes.cancelRun(runId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["wes-runs"] });
    },
  });

  const runDetailQuery = useQuery({
    queryKey: ["wes-run", detailRun?.run_id],
    queryFn: () => wes.getRun(detailRun!.run_id),
    enabled: detailOpen && !!detailRun?.run_id,
  });

  const handleDetails = useCallback((run: WesRunSummary) => {
    setDetailRun(run);
    setDetailOpen(true);
  }, []);

  const handleDetailsOpenChange = useCallback((open: boolean) => {
    setDetailOpen(open);
    if (!open) setDetailRun(null);
  }, []);

  const runDetailForModal: WesRunLog | null =
    runDetailQuery.data ??
    (detailRun
      ? {
          run_id: detailRun.run_id,
          state: detailRun.state,
          request: detailRun.workflow_url
            ? { workflow_url: detailRun.workflow_url }
            : undefined,
        }
      : null);

  const handleLogs = useCallback(
    async (run: WesRunSummary) => {
      setLogsRunId(run.run_id);
      setLogsContent({ stdout: "", stderr: "" });
      setLogsOpen(true);
      try {
        const full = await wes.getRun(run.run_id);
        const log = full.run_log;
        setLogsContent({
          stdout: log?.stdout ?? "",
          stderr: log?.stderr ?? "",
        });
      } catch {
        setLogsContent({
          stdout: "",
          stderr: "Logs konnten nicht geladen werden.",
        });
      }
    },
    []
  );

  const handleCancel = useCallback((run: WesRunSummary) => {
    cancelMutation.mutate(run.run_id);
  }, [cancelMutation]);

  const handleSubmit = useCallback(() => {
    submitMutation.mutate();
  }, [submitMutation]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Settings className="h-7 w-7 text-primary" />
        <h1 className="text-2xl font-semibold text-slate-800">Workflows (WES)</h1>
      </div>

      <StartPanel
        workflow={workflow}
        setWorkflow={setWorkflow}
        blastQuery={blastQuery}
        setBlastQuery={setBlastQuery}
        blastDatabase={blastDatabase}
        setBlastDatabase={setBlastDatabase}
        blastEvalue={blastEvalue}
        setBlastEvalue={setBlastEvalue}
        starFastqFiles={starFastqFiles}
        setStarFastqFiles={setStarFastqFiles}
        starReference={starReference}
        setStarReference={setStarReference}
        customUrl={customUrl}
        setCustomUrl={setCustomUrl}
        customParamsJson={customParamsJson}
        setCustomParamsJson={setCustomParamsJson}
        onSubmit={handleSubmit}
        isSubmitting={submitMutation.isPending}
      />

      <RunsTable
        runs={runs}
        isLoading={runsQuery.isLoading}
        onDetails={handleDetails}
        onCancel={handleCancel}
        onLogs={handleLogs}
      />

      <RunDetailModal
        run={runDetailForModal}
        open={detailOpen}
        onOpenChange={handleDetailsOpenChange}
      />

      <LogsModal
        runId={logsRunId ?? ""}
        stdout={logsContent.stdout}
        stderr={logsContent.stderr}
        open={logsOpen}
        onOpenChange={setLogsOpen}
      />
    </div>
  );
}
