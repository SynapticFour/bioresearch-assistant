import { useState, useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Copy, FileDown, Shield, CheckCircle2 } from "lucide-react";
import { pseudonymize as pseudonymizeApi } from "@/api/endpoints";
import type {
  EntityFound,
  PseudonymizeResult,
  AuditLogEntry,
} from "@/types";
import { useTranslation } from "@/hooks/useTranslation";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

const ENTITY_TYPE_COLORS: Record<string, string> = {
  PERSON: "bg-red-100 text-red-800 border-red-200",
  DATE: "bg-blue-100 text-blue-800 border-blue-200",
  DATE_TIME: "bg-blue-100 text-blue-800 border-blue-200",
  MEDICAL_RECORD: "bg-orange-100 text-orange-800 border-orange-200",
  MEDICAL_LICENSE: "bg-orange-100 text-orange-800 border-orange-200",
  PHONE_NUMBER: "bg-amber-100 text-amber-800 border-amber-200",
  EMAIL: "bg-violet-100 text-violet-800 border-violet-200",
};

function entityBadgeClass(type: string): string {
  return (
    ENTITY_TYPE_COLORS[type] ??
    "bg-slate-100 text-slate-800 border-slate-200"
  );
}

// Placeholder regex: <TYPE_1> or <TYPE_12>
const PLACEHOLDER_REGEX = /<([A-Z_0-9]+)_(\d+)>/g;

function highlightPseudonymizedText(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  PLACEHOLDER_REGEX.lastIndex = 0;
  while ((match = PLACEHOLDER_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const fullMatch = match[0];
    const type = match[1];
    parts.push(
      <span
        key={`${match.index}-${fullMatch}`}
        className={cn(
          "inline-flex items-center rounded border px-1 py-0.5 text-xs font-medium",
          entityBadgeClass(type)
        )}
      >
        {fullMatch}
      </span>
    );
    lastIndex = match.index + fullMatch.length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length > 0 ? parts : [text];
}

// --- Example texts ---

const EXAMPLE_ARZTBRIEF = `Patient Max Mustermann, geb. 15.03.1970, wurde am 22.01.2024 zur Abklärung einer Brustschwellung vorgestellt.
Anamnese: BRCA1-Mutation in der Familie. Kontakt: max.mustermann@email.de, Tel. 0711-123456.
Befund: Unauffällig. Überweisung an Frau Dr. Schmidt (Ärztin 4711).`;

const EXAMPLE_LABOR = `Laborbericht – Patientennummer: L-2024-98765
Datum: 10.02.2024 | Einsender: Dr. Anna Weber
HbA1c: 5,8 % | CRP: 2 mg/l
Hinweis: Nüchternblut entnommen um 08:00 Uhr.`;

// --- Left: Input (40%) ---

interface InputPanelProps {
  text: string;
  setText: (s: string) => void;
  language: "de" | "en";
  setLanguage: (l: "de" | "en") => void;
  onAnalyze: () => void;
  onPseudonymize: () => void;
  isAnalyzing: boolean;
  isPseudonymizing: boolean;
  analyzeLabel: string;
  languageLabel: string;
}

function InputPanel({
  text,
  setText,
  language,
  setLanguage,
  onAnalyze,
  onPseudonymize,
  isAnalyzing,
  isPseudonymizing,
  analyzeLabel,
  languageLabel,
}: InputPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <label className="text-sm font-medium text-slate-700">
        Klinischen Text eingeben
      </label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Klinischen Text eingeben..."
        rows={14}
        className="w-full resize-y rounded-lg border border-slate-300 p-3 text-slate-800 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        aria-label="Eingabetext"
      />
      <div>
        <span className="mb-1 block text-sm font-medium text-slate-700">
          {languageLabel}
        </span>
        <div className="flex rounded-lg border border-slate-300 p-0.5">
          <button
            type="button"
            onClick={() => setLanguage("de")}
            className={cn(
              "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
              language === "de"
                ? "bg-primary text-primary-foreground"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            DE
          </button>
          <button
            type="button"
            onClick={() => setLanguage("en")}
            className={cn(
              "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
              language === "en"
                ? "bg-primary text-primary-foreground"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            EN
          </button>
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={onAnalyze}
          disabled={!text.trim() || isAnalyzing || isPseudonymizing}
          className="flex-1"
        >
          {isAnalyzing ? "…" : analyzeLabel}
        </Button>
        <Button
          onClick={onPseudonymize}
          disabled={!text.trim() || isAnalyzing || isPseudonymizing}
          className="flex-1"
        >
          {isPseudonymizing ? "…" : "Pseudonymisieren"}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setText(EXAMPLE_ARZTBRIEF)}
          className="text-slate-600"
        >
          Beispiel: Arztbrief
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setText(EXAMPLE_LABOR)}
          className="text-slate-600"
        >
          Beispiel: Laborbericht
        </Button>
      </div>
    </div>
  );
}

// --- Middle: Output (40%) ---

interface OutputPanelProps {
  result: PseudonymizeResult | null;
  analyzeOnly: boolean;
  inputText: string;
  entitiesFromAnalyze: EntityFound[];
  onCopy: () => void;
  onExportPdf: () => void;
}

function OutputPanel({
  result,
  analyzeOnly,
  inputText,
  entitiesFromAnalyze,
  onCopy,
  onExportPdf,
}: OutputPanelProps) {
  const entities = result?.entities_found ?? entitiesFromAnalyze;
  const count = entities.length;

  return (
    <div className="flex flex-col gap-4">
      <label className="text-sm font-medium text-slate-700">
        {result ? "Pseudonymisierter Text" : "Ausgabe"}
      </label>
      {result ? (
        <div
          className="min-h-[200px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm text-slate-800 whitespace-pre-wrap break-words"
          role="textbox"
          aria-readonly
        >
          {highlightPseudonymizedText(result.pseudonymized_text)}
        </div>
      ) : analyzeOnly && inputText ? (
        <div className="min-h-[200px] w-full rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm text-slate-800 whitespace-pre-wrap">
          {inputText}
        </div>
      ) : (
        <textarea
          readOnly
          placeholder="Ergebnis erscheint hier nach Analysieren oder Pseudonymisieren."
          value=""
          rows={10}
          className="w-full resize-y rounded-lg border border-slate-300 bg-slate-50 p-3 text-slate-800 placeholder:text-slate-400"
        />
      )}
      {count > 0 && (
        <>
          <div className="flex flex-wrap gap-1.5">
            {entities.map((e, i) => (
              <Badge
                key={`${e.type}-${e.start}-${i}`}
                className={cn(
                  "border text-xs",
                  entityBadgeClass(e.type)
                )}
              >
                {e.type}
              </Badge>
            ))}
          </div>
          <p className="text-sm text-slate-600">
            {count} {count === 1 ? "Entity" : "Entities"} erkannt
            {result ? " und ersetzt" : ""}
          </p>
        </>
      )}
      {result && result.pseudonymized_text && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onCopy}>
            <Copy className="h-4 w-4" />
            Text kopieren
          </Button>
          <Button variant="outline" size="sm" onClick={onExportPdf}>
            <FileDown className="h-4 w-4" />
            Als PDF exportieren
          </Button>
        </div>
      )}
    </div>
  );
}

// --- Right: Info panel (20%) ---

interface InfoPanelProps {
  entities: EntityFound[];
  mappingId: string | null;
}

function InfoPanel({ entities, mappingId }: InfoPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold text-slate-800">
        Erkannte Entities
      </h3>
      {entities.length === 0 ? (
        <p className="text-xs text-slate-500">Keine Entities.</p>
      ) : (
        <ul className="space-y-2">
          {entities.map((e, i) => (
            <li
              key={`${e.type}-${e.start}-${i}`}
              className="flex items-center justify-between gap-2 rounded border border-slate-200 bg-white px-2 py-1.5 text-xs"
            >
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 font-medium",
                  entityBadgeClass(e.type)
                )}
              >
                {e.type}
              </span>
              <span className="text-slate-500">
                {e.start}–{e.end}
              </span>
            </li>
          ))}
        </ul>
      )}
      {mappingId && (
        <div>
          <h3 className="mb-1 text-sm font-semibold text-slate-800">
            Mapping ID
          </h3>
          <p className="break-all rounded border border-slate-200 bg-slate-50 px-2 py-1.5 font-mono text-xs text-slate-600">
            {mappingId}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Für Wiederherstellung (verschlüsselt gespeichert)
          </p>
        </div>
      )}
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <h3 className="mb-2 text-sm font-semibold text-slate-800">
          DSGVO Info
        </h3>
        <ul className="space-y-1.5 text-xs text-slate-700">
          <li className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
            Daten verlassen dieses System nicht
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
            Vollständig audit-logged
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
            Reversibel für Berechtigte
          </li>
        </ul>
      </div>
    </div>
  );
}

// --- Audit log table ---

interface AuditLogTableProps {
  entries: AuditLogEntry[];
  onReverseClick?: (mappingId: string) => void;
  isReversing?: boolean;
}

function AuditLogTable({
  entries,
  onReverseClick,
  isReversing,
}: AuditLogTableProps) {
  const displayList = entries.slice(0, 50);

  function formatTime(iso: string): string {
    try {
      return new Date(iso).toLocaleString("de-DE", {
        dateStyle: "short",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-slate-600">
            <th className="pb-2 pr-4 font-medium">Zeitstempel</th>
            <th className="pb-2 pr-4 font-medium">Entities</th>
            <th className="pb-2 pr-4 font-medium">Typ</th>
            {onReverseClick && (
              <th className="pb-2 font-medium">Aktion</th>
            )}
          </tr>
        </thead>
        <tbody>
          {displayList.length === 0 ? (
            <tr>
              <td
                colSpan={onReverseClick ? 4 : 3}
                className="py-4 text-center text-slate-500"
              >
                Noch keine Einträge
              </td>
            </tr>
          ) : (
            displayList.map((e) => (
              <tr key={e.operation_id} className="border-b border-slate-100">
                <td className="py-2 pr-4 text-slate-700">
                  {formatTime(e.timestamp)}
                </td>
                <td className="py-2 pr-4">{e.entities_count}</td>
                <td className="py-2 pr-4">{e.operation_type}</td>
                {onReverseClick && (
                  <td className="py-2">
                    {e.mapping_id ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isReversing}
                        onClick={() => onReverseClick(e.mapping_id!)}
                      >
                        De-pseudonymisieren
                      </Button>
                    ) : (
                      "—"
                    )}
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

// --- PDF export: open print dialog with content ---

function exportPseudonymizedPdf(text: string): void {
  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(`
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Pseudonymisierter Text</title>
    <style>body{font-family:system-ui,sans-serif;padding:2rem;max-width:60rem;margin:0 auto;white-space:pre-wrap;}</style>
    </head><body><pre>${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre></body></html>
  `);
  win.document.close();
  win.focus();
  setTimeout(() => {
    win.print();
    win.close();
  }, 300);
}

// --- Main page ---

type TabId = "main" | "audit" | "depseudo";

export function PseudonymizePage() {
  const features = useFeatureFlags();
  const [text, setText] = useState("");
  const [activeTab, setActiveTab] = useState<TabId>("main");
  const [confirmReverseMappingId, setConfirmReverseMappingId] = useState<
    string | null
  >(null);
  const [reverseResult, setReverseResult] = useState<{
    mapping_id: string;
    original_text: string;
    pseudonymized_text: string;
    accessed_by: string;
    access_time: string;
  } | null>(null);
  const { t, language, changeLanguage } = useTranslation();
  const [result, setResult] = useState<PseudonymizeResult | null>(null);
  const [analyzeOnlyEntities, setAnalyzeOnlyEntities] = useState<
    EntityFound[]
  >([]);
  const [analyzeOnlyMode, setAnalyzeOnlyMode] = useState(false);

  const auditQuery = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => pseudonymizeApi.getAuditLog(),
  });
  const auditEntries = auditQuery.data ?? [];
  const reversibleEntries = auditEntries.filter(
    (e) => e.mapping_id != null && e.mapping_id !== ""
  );

  const [reverseError, setReverseError] = useState<string | null>(null);
  const reverseMutation = useMutation({
    mutationFn: (mappingId: string) => pseudonymizeApi.reverse(mappingId),
    onSuccess: (data) => {
      setConfirmReverseMappingId(null);
      setReverseResult(data);
      setReverseError(null);
      auditQuery.refetch();
    },
    onError: (err: Error & { response?: { status?: number } }) => {
      setConfirmReverseMappingId(null);
      const status = err?.response?.status;
      const message =
        status === 403
          ? "Sie haben keine Berechtigung zur De-Pseudonymisierung dieses Eintrags."
          : err?.message ?? "Fehler bei der De-Pseudonymisierung.";
      setReverseError(message);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: ({ t, lang }: { t: string; lang: string }) =>
      pseudonymizeApi.analyze(t, lang),
    onSuccess: (data) => {
      setAnalyzeOnlyEntities(data.entities_found);
      setAnalyzeOnlyMode(true);
      setResult(null);
    },
  });

  const pseudonymizeMutation = useMutation({
    mutationFn: ({ t, lang }: { t: string; lang: string }) =>
      pseudonymizeApi.pseudonymize(t, lang),
    onSuccess: (data) => {
      setResult(data);
      setAnalyzeOnlyMode(false);
      setAnalyzeOnlyEntities([]);
    },
  });

  const handleAnalyze = useCallback(() => {
    const t = text.trim();
    if (!t) return;
    analyzeMutation.mutate({ t, lang: language });
  }, [text, language, analyzeMutation]);

  const handlePseudonymize = useCallback(() => {
    const t = text.trim();
    if (!t) return;
    pseudonymizeMutation.mutate({ t, lang: language });
  }, [text, language, pseudonymizeMutation]);

  const handleCopy = useCallback(() => {
    const toCopy = result?.pseudonymized_text ?? "";
    if (toCopy) {
      void navigator.clipboard.writeText(toCopy);
    }
  }, [result]);

  const handleExportPdf = useCallback(() => {
    const toExport = result?.pseudonymized_text ?? "";
    if (toExport) exportPseudonymizedPdf(toExport);
  }, [result]);

  const entities = result?.entities_found ?? analyzeOnlyEntities;
  const mappingId = result?.mapping_id ?? null;

  const handleReverseClick = useCallback((mappingIdToReverse: string) => {
    setConfirmReverseMappingId(mappingIdToReverse);
  }, []);

  const handleConfirmReverse = useCallback(() => {
    if (confirmReverseMappingId) reverseMutation.mutate(confirmReverseMappingId);
  }, [confirmReverseMappingId, reverseMutation]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Shield className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-semibold text-slate-800">
            {t("pseudonymize", "title")}
          </h1>
        </div>
        <div className="flex rounded-lg border border-slate-200 p-0.5">
          <button
            type="button"
            onClick={() => setActiveTab("main")}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              activeTab === "main"
                ? "bg-primary text-primary-foreground"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            Pseudonymisieren
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("audit")}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              activeTab === "audit"
                ? "bg-primary text-primary-foreground"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            Audit Log
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("depseudo")}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              activeTab === "depseudo"
                ? "bg-primary text-primary-foreground"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            De-Pseudonymisierung
          </button>
        </div>
      </div>
      {activeTab === "main" && (
        <>
          {features.spacy_ner ? (
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-900">
              ✓ NLP-Erkennung aktiv (Namen, Orte, etc.)
            </div>
          ) : (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              ℹ️ Basis-Erkennung (Datum, Email, Telefon). Für vollständige
              NLP-Erkennung: lokale Installation mit spaCy.
            </div>
          )}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <InputPanel
                text={text}
                setText={setText}
                language={language}
                setLanguage={changeLanguage}
                onAnalyze={handleAnalyze}
                onPseudonymize={handlePseudonymize}
                isAnalyzing={analyzeMutation.isPending}
                isPseudonymizing={pseudonymizeMutation.isPending}
                analyzeLabel={t("pseudonymize", "analyze")}
                languageLabel={t("pseudonymize", "language")}
              />
            </div>
            <div className="lg:col-span-2">
              <OutputPanel
                result={result}
                analyzeOnly={analyzeOnlyMode}
                inputText={text}
                entitiesFromAnalyze={analyzeOnlyEntities}
                onCopy={handleCopy}
                onExportPdf={handleExportPdf}
              />
            </div>
            <div className="lg:col-span-1">
              <InfoPanel entities={entities} mappingId={mappingId} />
            </div>
          </div>
        </>
      )}

      {activeTab === "audit" && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            Audit Log
          </h2>
          <p className="mb-3 text-sm text-slate-500">
            Letzte Pseudonymisierungen (nur Metadaten, kein Originaltext)
          </p>
          {auditQuery.isLoading ? (
            <div className="h-24 animate-pulse rounded bg-slate-100" />
          ) : (
            <AuditLogTable
              entries={auditEntries}
              onReverseClick={handleReverseClick}
              isReversing={reverseMutation.isPending}
            />
          )}
        </section>
      )}

      {activeTab === "depseudo" && (
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">
            De-Pseudonymisierung
          </h2>
          <p className="mb-3 text-sm text-slate-500">
            Einträge mit Mapping-ID, die Sie de-pseudonymisieren dürfen.
          </p>
          {auditQuery.isLoading ? (
            <div className="h-24 animate-pulse rounded bg-slate-100" />
          ) : reversibleEntries.length === 0 ? (
            <p className="py-4 text-slate-500">
              Keine Einträge mit Mapping-ID vorhanden.
            </p>
          ) : (
            <AuditLogTable
              entries={reversibleEntries}
              onReverseClick={handleReverseClick}
              isReversing={reverseMutation.isPending}
            />
          )}
        </section>
      )}

      {/* Confirm De-Pseudonymization */}
      <Dialog
        open={confirmReverseMappingId != null}
        onOpenChange={(open) => !open && setConfirmReverseMappingId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>⚠️ De-Pseudonymisierung</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-700">
            Sie sind dabei, die Pseudonymisierung aufzuheben. Dieser Vorgang
            wird im Audit Log protokolliert. Sind Sie sicher?
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmReverseMappingId(null)}
            >
              Abbrechen
            </Button>
            <Button
              onClick={handleConfirmReverse}
              disabled={reverseMutation.isPending}
            >
              De-pseudonymisieren
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Result / Error after De-Pseudonymization */}
      <Dialog
        open={reverseResult != null || reverseError != null}
        onOpenChange={(open) => {
          if (!open) {
            setReverseResult(null);
            setReverseError(null);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {reverseError ? "Fehler" : "De-Pseudonymisierung — Ergebnis"}
          </DialogTitle>
        </DialogHeader>
        {reverseError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {reverseError}
          </p>
        ) : reverseResult ? (
          <div className="space-y-4 text-sm">
            <div>
              <h4 className="mb-1 font-medium text-slate-800">Original Text</h4>
              <pre className="max-h-40 overflow-auto rounded border border-slate-200 bg-slate-50 p-3 whitespace-pre-wrap">
                {reverseResult.original_text}
              </pre>
            </div>
            <div>
              <h4 className="mb-1 font-medium text-slate-800">
                Pseudonymisierter Text
              </h4>
              <pre className="max-h-40 overflow-auto rounded border border-slate-200 bg-slate-50 p-3 whitespace-pre-wrap">
                {reverseResult.pseudonymized_text}
              </pre>
            </div>
            <p className="text-slate-500">
              Zugriff: {reverseResult.accessed_by} —{" "}
              {new Date(reverseResult.access_time).toLocaleString("de-DE")}
            </p>
            <p className="rounded border border-amber-200 bg-amber-50 p-2 text-amber-900">
              Dieser Zugriff wurde protokolliert.
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <Button
            onClick={() => {
              setReverseResult(null);
              setReverseError(null);
            }}
          >
            Schließen
          </Button>
        </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
