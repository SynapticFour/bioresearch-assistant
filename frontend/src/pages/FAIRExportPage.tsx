import type { ChangeEvent } from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, Loader2, Upload } from "lucide-react";
import { fairExport as fairExportApi } from "@/api/endpoints";
import type { FAIRExportOptions, FAIRComplianceReport } from "@/api/endpoints";
import { useTranslation } from "@/hooks/useTranslation";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";

const LICENSES = ["CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "MIT", "Apache-2.0"];

type Step = 1 | 2 | 3;

export default function FAIRExportPage() {
  const { t } = useTranslation();
  const { showSuccess, showError } = useToast();
  const [step, setStep] = useState<Step>(1);
  const [options, setOptions] = useState<FAIRExportOptions>({
    title: "",
    description: "",
    authors: [],
    license: "CC-BY-4.0",
    include_papers: true,
    include_phenopackets: true,
    include_notebooks: true,
    include_drs: false,
    keywords: [],
    funding: undefined,
  });
  const [preview, setPreview] = useState<{
    papers_count: number;
    phenopackets_count: number;
    notebooks_count: number;
  } | null>(null);
  const [compliance, setCompliance] = useState<FAIRComplianceReport | null>(null);
  const [authorsText, setAuthorsText] = useState("");
  const [keywordsText, setKeywordsText] = useState("");

  const previewMutation = useMutation({
    mutationFn: () => fairExportApi.preview(options),
    onSuccess: (data) => setPreview(data),
  });


  const downloadMutation = useMutation({
    mutationFn: () => fairExportApi.download(options),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${options.title || "fair_export"}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      showSuccess("ZIP heruntergeladen");
    },
    onError: () => showError("Download fehlgeschlagen"),
  });

  const goToStep2 = () => {
    const next = {
      ...options,
      authors: authorsText.split(",").map((s) => s.trim()).filter(Boolean),
      keywords: keywordsText.split(",").map((s) => s.trim()).filter(Boolean),
    };
    setOptions(next);
    previewMutation.mutate();
    setStep(2);
  };

  const goToStep3 = () => {
    const next = {
      ...options,
      authors: authorsText.split(",").map((s) => s.trim()).filter(Boolean),
      keywords: keywordsText.split(",").map((s) => s.trim()).filter(Boolean),
    };
    setOptions(next);
    fairExportApi.complianceCheck(next).then(setCompliance);
    setStep(3);
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold text-slate-800">
        📦 {t("nav", "fairExport")}
      </h1>

      {/* Step indicator */}
      <div className="flex gap-2">
        {([1, 2, 3] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStep(s)}
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              step === s ? "bg-primary text-primary-foreground" : "bg-slate-200 text-slate-600"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Step 1: What to export */}
      {step === 1 && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-slate-800">Was exportieren?</h2>
          <ul className="space-y-3">
            <li className="flex items-center gap-3">
              <input
                type="checkbox"
                id="include_papers"
                checked={options.include_papers}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({ ...o, include_papers: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300"
              />
              <label htmlFor="include_papers">Literatur (Papers)</label>
            </li>
            <li className="flex items-center gap-3">
              <input
                type="checkbox"
                id="include_phenopackets"
                checked={options.include_phenopackets}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({ ...o, include_phenopackets: e.target.checked }))
                }
                className="h-4 w-4 rounded border-slate-300"
              />
              <label htmlFor="include_phenopackets">Phenopackets</label>
            </li>
            <li className="flex items-center gap-3">
              <input
                type="checkbox"
                id="include_notebooks"
                checked={options.include_notebooks}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({ ...o, include_notebooks: e.target.checked }))
                }
                className="h-4 w-4 rounded border-slate-300"
              />
              <label htmlFor="include_notebooks">Notizbücher</label>
            </li>
            <li className="flex items-center gap-3">
              <input
                type="checkbox"
                id="include_drs"
                checked={options.include_drs}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({ ...o, include_drs: e.target.checked }))}
                className="h-4 w-4 rounded border-slate-300"
              />
              <label htmlFor="include_drs">DRS-Dateien (optional, oft groß)</label>
            </li>
          </ul>
          <Button className="mt-4" onClick={goToStep2}>
            Weiter → Metadaten
          </Button>
        </div>
      )}

      {/* Step 2: Metadata */}
      {step === 2 && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-slate-800">Metadaten</h2>
          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
            <div>
              <label htmlFor="title" className="mb-1 block text-sm font-medium text-slate-600">
                Titel
              </label>
              <input
                id="title"
                value={options.title}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({ ...o, title: e.target.value }))}
                placeholder="Projekt- oder Datensatz-Titel"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label htmlFor="license" className="mb-1 block text-sm font-medium text-slate-600">
                Lizenz
              </label>
              <select
                id="license"
                value={options.license}
                onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                  setOptions((o) => ({ ...o, license: e.target.value }))}
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
              >
                {LICENSES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-600">
                Beschreibung
              </label>
              <textarea
                id="description"
                value={options.description ?? ""}
                onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
                  setOptions((o) => ({ ...o, description: e.target.value }))}
                placeholder="Kurze Beschreibung des Datensatzes"
                className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
                rows={3}
              />
            </div>
            <div>
              <label htmlFor="authors" className="mb-1 block text-sm font-medium text-slate-600">
                Autoren (kommagetrennt)
              </label>
              <input
                id="authors"
                value={authorsText}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setAuthorsText(e.target.value)}
                placeholder="Name 1, Name 2"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label htmlFor="funding" className="mb-1 block text-sm font-medium text-slate-600">
                Förderung
              </label>
              <input
                id="funding"
                value={options.funding ?? ""}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setOptions((o) => ({
                    ...o,
                    funding: e.target.value.trim() || undefined,
                  }))
                }
                placeholder="z.B. DFG 123456"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="keywords" className="mb-1 block text-sm font-medium text-slate-600">
                Keywords (kommagetrennt)
              </label>
              <input
                id="keywords"
                value={keywordsText}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setKeywordsText(e.target.value)}
                placeholder="keyword1, keyword2"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Button variant="outline" onClick={() => setStep(1)}>
              ← Zurück
            </Button>
            <Button onClick={goToStep3}>
              Weiter → FAIR & Export
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: FAIR compliance & export */}
      {step === 3 && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-medium text-slate-800">FAIR Compliance & Export</h2>
          {preview && (
            <p className="mb-2 text-sm text-slate-600">
              Enthalten: {preview.papers_count} Papers, {preview.phenopackets_count} Phenopackets,{" "}
              {preview.notebooks_count} Notizbücher
            </p>
          )}
          {compliance === null && (
            <p className="mb-2 text-sm text-slate-500">FAIR-Bewertung wird geladen…</p>
          )}
          {compliance && (
            <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="mb-2 font-medium">
                FAIR Score: {compliance.score}/100{" "}
                {compliance.score >= 80 ? "✅" : compliance.score >= 60 ? "⚠️" : "❌"}
              </p>
              <ul className="space-y-1 text-sm">
                <li>F Findable: {compliance.findable ? "✅" : "⚠️"}</li>
                <li>A Accessible: {compliance.accessible ? "✅" : "⚠️"}</li>
                <li>I Interoperable: {compliance.interoperable ? "✅" : "⚠️"}</li>
                <li>R Reusable: {compliance.reusable ? "✅" : "⚠️"}</li>
              </ul>
              {compliance.recommendations.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-slate-600">Empfehlungen:</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                    {compliance.recommendations.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => downloadMutation.mutate()}
              disabled={downloadMutation.isPending}
            >
              {downloadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  ZIP Herunterladen
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                fairExportApi.zenodo(options).then(
                  (res) => showSuccess(res.message ?? "Zenodo Upload gestartet"),
                  () => showError("Zenodo Upload fehlgeschlagen (ZENODO_TOKEN konfigurieren?)")
                )
              }
            >
              <Upload className="mr-2 h-4 w-4" />
              Zu Zenodo hochladen
            </Button>
          </div>
          <div className="mt-4">
            <Button variant="ghost" onClick={() => setStep(2)}>
              ← Zurück zu Metadaten
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
