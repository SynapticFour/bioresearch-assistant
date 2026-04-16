import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, Loader2, Share2 } from "lucide-react";
import { miiExport } from "@/api/endpoints";
import { useTranslation } from "@/hooks/useTranslation";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";

const ALL_MODULES = ["diagnosis", "laboratory", "biospecimen", "genomics"] as const;

export default function MIIExportPage() {
  const { t } = useTranslation();
  const { showSuccess, showError } = useToast();
  const [pseudonyms, setPseudonyms] = useState("");
  const [projects, setProjects] = useState("");
  const [modules, setModules] = useState<Set<string>>(
    new Set(ALL_MODULES)
  );
  const [jsonPreview, setJsonPreview] = useState<string>("");

  const exportMutation = useMutation({
    mutationFn: () =>
      miiExport.exportBundle({
        pseudonym_ids: pseudonyms
          .split(/[\s,]+/)
          .map((s) => s.trim())
          .filter(Boolean),
        modules: Array.from(modules) as (
          | "diagnosis"
          | "laboratory"
          | "biospecimen"
          | "genomics"
        )[],
        research_project_ids: projects
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: (data) => {
      setJsonPreview(JSON.stringify(data.bundle, null, 2));
      showSuccess("Bundle erzeugt");
    },
    onError: () => showError("Export fehlgeschlagen (Consent prüfen)"),
  });

  const downloadJson = () => {
    if (!jsonPreview) return;
    const blob = new Blob([jsonPreview], { type: "application/fhir+json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mii-bundle.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleModule = (m: string) => {
    setModules((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-4xl">
      <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
        <Share2 className="h-6 w-6" />
        {t("nav", "miiExport")}
      </h1>
      <p className="text-sm text-slate-600">
        MII-KDS-orientierter FHIR-Bundle-Export (JSON). Aktiver Broad Consent
        für die gewählten Pseudonyme ist erforderlich.
      </p>

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
        <label className="block text-sm font-medium text-slate-700">
          Pseudonym-IDs (Leerzeichen oder Komma)
        </label>
        <textarea
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono min-h-[80px]"
          value={pseudonyms}
          onChange={(e) => setPseudonyms(e.target.value)}
          placeholder="PP-001 PP-002"
        />
        <label className="block text-sm font-medium text-slate-700">
          Optional: Projekt-IDs für Consent-Prüfung
        </label>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={projects}
          onChange={(e) => setProjects(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {ALL_MODULES.map((m) => (
            <label key={m} className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={modules.has(m)}
                onChange={() => toggleModule(m)}
              />
              {m}
            </label>
          ))}
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            disabled={exportMutation.isPending || !pseudonyms.trim()}
            onClick={() => exportMutation.mutate()}
          >
            {exportMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Bundle erzeugen
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!jsonPreview}
            onClick={downloadJson}
          >
            <Download className="mr-2 h-4 w-4" />
            JSON
          </Button>
        </div>
      </div>

      {jsonPreview && (
        <pre className="text-xs overflow-auto max-h-[480px] rounded border border-slate-200 bg-slate-50 p-4">
          {jsonPreview}
        </pre>
      )}
    </div>
  );
}
