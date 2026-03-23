import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ClipboardList, Dna, Search, Upload } from "lucide-react";
import type {
  PhenoFlowRunRequest,
  PhenoFlowRunResponse,
  PhenoFlowFileType,
} from "@/api/endpoints";
import { phenoflow } from "@/api/endpoints";

type PhenoFlowTab = "query" | "matches" | "submit" | "history";

function parseTerms(raw: string): string[] {
  return raw
    .split(/[\n,]+/g)
    .map((s) => s.trim())
    .filter(Boolean);
}

const DEFAULT_PARAMS_TEMPLATE: Record<string, unknown> = {
  // v0.1 placeholders:
  // {{drs_object_id}}, {{drs_stream_url}}, {{pseudonym_id}}, {{file_type}}
  input_bam: "{{drs_stream_url}}",
};

export function PhenoFlowPage() {
  const { showError, showSuccess } = useToast();
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<PhenoFlowTab>("query");
  const [hpoTermsRaw, setHpoTermsRaw] = useState<string>("HP:0001250");
  const [fileType, setFileType] = useState<PhenoFlowFileType | "">("");

  const [workflowUrl, setWorkflowUrl] = useState<string>("nextflow");
  const [workflowParamsTemplateRaw, setWorkflowParamsTemplateRaw] = useState<string>(
    JSON.stringify(DEFAULT_PARAMS_TEMPLATE, null, 2)
  );

  const [lastRun, setLastRun] = useState<PhenoFlowRunResponse | null>(null);
  const [history, setHistory] = useState<PhenoFlowRunResponse[]>([]);

  const workflowParamsTemplate = useMemo(() => {
    try {
      const parsed = JSON.parse(workflowParamsTemplateRaw) as Record<string, unknown>;
      return parsed;
    } catch {
      return null;
    }
  }, [workflowParamsTemplateRaw]);

  const createRunMutation = useMutation({
    mutationFn: async () => {
      const hpo_terms = parseTerms(hpoTermsRaw);
      if (!hpo_terms.length) {
        throw new Error("Bitte mindestens einen HPO Term angeben.");
      }
      if (!workflowParamsTemplate) {
        throw new Error("workflow_params_template muss gültiges JSON sein.");
      }

      const payload: PhenoFlowRunRequest = {
        hpo_terms,
        file_type: fileType ? fileType : null,
        limit_matches: 50,
        workflow_url: workflowUrl,
        workflow_type: "NEXTFLOW",
        workflow_type_version: "DSL2",
        workflow_params_template: workflowParamsTemplate,
      };

      return phenoflow.createRun(payload);
    },
    onSuccess: (data: PhenoFlowRunResponse) => {
      setLastRun(data);
      setHistory((h) => [data, ...h].slice(0, 20));
      queryClient.invalidateQueries();
      showSuccess("PhenoFlow Run gestartet");
      setTab("matches");
    },
    onError: (err: Error) => showError(err?.message ?? "PhenoFlow Start fehlgeschlagen"),
  });

  const runItems = lastRun?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800">PhenoFlow</h1>
        <div className="flex flex-wrap gap-2">
          <Button variant={tab === "query" ? "default" : "outline"} onClick={() => setTab("query")}>
            <Search className="mr-2 h-4 w-4" />
            Query
          </Button>
          <Button
            variant={tab === "matches" ? "default" : "outline"}
            onClick={() => setTab("matches")}
            disabled={!lastRun}
          >
            <Dna className="mr-2 h-4 w-4" />
            Matches
          </Button>
          <Button
            variant={tab === "submit" ? "default" : "outline"}
            onClick={() => setTab("submit")}
            disabled={!lastRun}
          >
            <Upload className="mr-2 h-4 w-4" />
            Submit
          </Button>
          <Button
            variant={tab === "history" ? "default" : "outline"}
            onClick={() => setTab("history")}
          >
            <ClipboardList className="mr-2 h-4 w-4" />
            History
          </Button>
        </div>
      </div>

      {tab === "query" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="space-y-4">
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
              🔒 DSGVO: PhenoFlow speichert nur Identifikatoren (pseudonym_id / drs_object_id / WES run_id),
              keine klinischen Texte oder dekodierten Genomdaten.
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800">HPO Terms</label>
              <textarea
                className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-800"
                rows={4}
                value={hpoTermsRaw}
                onChange={(e) => setHpoTermsRaw(e.target.value)}
                placeholder="HP:0001250, HP:0000707"
              />
              <p className="text-xs text-slate-500">Komma- oder zeilen-getrennt.</p>
            </div>

            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[220px] space-y-2">
                <label className="text-sm font-medium text-slate-800">Asset Type (optional)</label>
                <select
                  className="w-full rounded-lg border border-slate-300 bg-white p-2 text-sm"
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value as PhenoFlowFileType | "")}
                >
                  <option value="">Any</option>
                  <option value="bam">bam</option>
                  <option value="cram">cram</option>
                  <option value="vcf">vcf</option>
                  <option value="fastq">fastq</option>
                  <option value="other">other</option>
                </select>
              </div>
              <div className="flex-1 min-w-[220px] space-y-2">
                <label className="text-sm font-medium text-slate-800">Workflow URL / Descriptor</label>
                <input
                  className="w-full rounded-lg border border-slate-300 bg-white p-2 text-sm"
                  value={workflowUrl}
                  onChange={(e) => setWorkflowUrl(e.target.value)}
                />
                <p className="text-xs text-slate-500">Wird von WES validiert.</p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-800">
                workflow_params_template (JSON)
              </label>
              <textarea
                className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm font-mono"
                rows={6}
                value={workflowParamsTemplateRaw}
                onChange={(e) => setWorkflowParamsTemplateRaw(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={() => createRunMutation.mutate()}
                disabled={createRunMutation.isPending}
              >
                {createRunMutation.isPending ? "Starten…" : "PhenoFlow Run starten"}
              </Button>
              {!workflowParamsTemplate && (
                <Badge variant="secondary" className="bg-red-50 text-red-700">
                  Ungültiges JSON
                </Badge>
              )}
            </div>

            {lastRun && (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">Run: {lastRun.phenoflow_run_id}</Badge>
                  <Badge variant="secondary">
                    Submitted: {lastRun.submitted_count}
                  </Badge>
                  <Badge variant="secondary">Matched: {lastRun.matched_count}</Badge>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "matches" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          {!lastRun ? (
            <div className="text-sm text-slate-600">Noch kein Run gestartet.</div>
          ) : runItems.length === 0 ? (
            <div className="text-sm text-slate-600">Keine Treffer / alle Matches fehlerhaft.</div>
          ) : (
            <div className="space-y-3">
              {runItems.map((it, idx) => (
                <div
                  key={`${it.drs_object_id}-${idx}`}
                  className="rounded-md border border-slate-200 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2 justify-between">
                    <div className="min-w-[220px]">
                      <div className="text-sm font-medium text-slate-800">
                        {it.pseudonym_id}
                      </div>
                      <div className="text-xs text-slate-600">{it.drs_object_id}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{it.file_type}</Badge>
                      <Badge variant="outline">{it.state_snapshot}</Badge>
                    </div>
                  </div>
                  {it.error && (
                    <div className="mt-2 text-xs text-red-700">
                      Fehler: {it.error}
                    </div>
                  )}
                  {it.wes_run_id && (
                    <div className="mt-2 text-xs text-slate-600">
                      WES run_id: <span className="font-mono">{it.wes_run_id}</span>
                    </div>
                  )}
                </div>
              ))}
              {lastRun.errors.length > 0 && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  <div className="font-medium">Aggregierte Fehler</div>
                  <div className="mt-1 space-y-1">
                    {lastRun.errors.map((e) => (
                      <div key={e} className="text-xs">
                        {e}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === "submit" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          {!lastRun ? (
            <div className="text-sm text-slate-600">Noch kein Run gestartet.</div>
          ) : (
            <div className="space-y-3 text-sm">
              <div className="font-medium text-slate-800">Run Request (v0.1)</div>
              <div className="text-slate-600">
                Dieser Tab ist eine UX-Vorbereitung für spätere Workflow-Parameter-Vorschau und
                “Batch submit”.
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <div className="text-xs text-slate-700">
                  Run: <span className="font-mono">{lastRun.phenoflow_run_id}</span>
                </div>
                <div className="mt-1 text-xs text-slate-700">
                  Submitted: {lastRun.submitted_count} / Matched pairs: {lastRun.matched_count}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setTab("history")}
                >
                  Zur History
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "history" && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          {history.length === 0 ? (
            <div className="text-sm text-slate-600">Keine Run-Historie vorhanden.</div>
          ) : (
            <div className="space-y-3">
              {history.map((h) => (
                <div key={h.phenoflow_run_id} className="rounded-md border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-slate-800">
                        {h.phenoflow_run_id}
                      </div>
                      <div className="text-xs text-slate-600">
                        Submitted: {h.submitted_count} | Matched: {h.matched_count}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="outline">{h.items.length} items</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

