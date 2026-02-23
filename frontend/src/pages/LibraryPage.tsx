import { useState, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Plus,
  Trash2,
  Search,
  Package,
} from "lucide-react";
import { library as libraryApi } from "@/api/endpoints";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { useToast } from "@/contexts/ToastContext";
import type { Paper } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const PUBMED_URL = (pmid: string) =>
  `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;

interface PaperCardProps {
  paper: Paper;
  summaryOverride?: string | null;
  summaryCached?: boolean;
  onRemove: (pmid: string) => void;
  onSummarize?: (pmid: string) => void;
  isRemoving: boolean;
  isSummarizing?: boolean;
}

function PaperCard({
  paper,
  summaryOverride,
  summaryCached,
  onRemove,
  onSummarize,
  isRemoving,
  isSummarizing,
}: PaperCardProps) {
  const [abstractExpanded, setAbstractExpanded] = useState(false);
  const abstract = paper.abstract ?? "";
  const lineClamp = abstractExpanded ? undefined : 3;
  const displaySummary = summaryOverride ?? paper.summary;
  const showCachedBadge = displaySummary && (summaryCached ?? !!paper.summary);
  const isFromCache = summaryCached ?? !!paper.summary;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-1 text-base font-bold text-slate-800">
        {paper.title || `PMID ${paper.pmid}`}
      </h3>
      <p className="mb-2 text-sm text-slate-500">
        {(paper.authors ?? []).slice(0, 5).join(", ")}
        {(paper.authors?.length ?? 0) > 5 && " et al."}
        {paper.year != null && ` · ${paper.year}`}
        {paper.journal && ` · ${paper.journal}`}
      </p>
      {abstract && (
        <div className="mb-3">
          <p
            className="text-sm text-slate-700"
            style={
              lineClamp
                ? {
                    display: "-webkit-box",
                    WebkitLineClamp: lineClamp,
                    WebkitBoxOrient: "vertical" as const,
                    overflow: "hidden",
                  }
                : undefined
            }
          >
            {abstract}
          </p>
          {abstract.length > 200 && (
            <button
              type="button"
              onClick={() => setAbstractExpanded((e) => !e)}
              className="mt-1 flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              {abstractExpanded ? (
                <>
                  Weniger <ChevronUp className="h-4 w-4" />
                </>
              ) : (
                <>
                  Mehr <ChevronDown className="h-4 w-4" />
                </>
              )}
            </button>
          )}
        </div>
      )}
      {displaySummary && (
        <div className="mb-3 rounded-lg border border-teal-100 bg-teal-50 p-3 text-sm text-slate-800">
          <h4 className="font-medium text-teal-800">KI-Zusammenfassung</h4>
          <p className="mt-1">{displaySummary}</p>
          {showCachedBadge && (
            <span className="mt-2 block text-xs text-gray-400">
              {isFromCache ? "📦 Gespeicherte Zusammenfassung" : "✨ Neu generiert"}
            </span>
          )}
        </div>
      )}
      {onSummarize && (
        <div className="mb-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onSummarize(paper.pmid)}
            disabled={isSummarizing}
            className="summarize-btn"
          >
            {isSummarizing ? "⏳ Zusammenfasse…" : "🤖 KI-Zusammenfassung"}
          </Button>
        </div>
      )}
      <footer className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
        <Badge variant="outline" className="font-mono text-xs">
          PMID {paper.pmid}
        </Badge>
        <a
          href={PUBMED_URL(paper.pmid)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          In PubMed öffnen
          <ExternalLink className="h-4 w-4" />
        </a>
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={() => onRemove(paper.pmid)}
          disabled={isRemoving}
        >
          <Trash2 className="h-4 w-4" />
          Entfernen
        </Button>
      </footer>
    </article>
  );
}

const initialPaperForm = {
  title: "",
  authors: "",
  year: "",
  journal: "",
  doi: "",
  pmid: "",
  abstract: "",
  tags: "",
};

export function LibraryPage() {
  const queryClient = useQueryClient();
  const features = useFeatureFlags();
  const { showSuccess, showError } = useToast();

  const [addPaperOpen, setAddPaperOpen] = useState(false);
  const [paperForm, setPaperForm] = useState(initialPaperForm);
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkResult, setBulkResult] = useState<{
    imported: number;
    skipped: number;
    errors: string[];
  } | null>(null);

  const [semanticQuery, setSemanticQuery] = useState("");
  const [yearFilter, setYearFilter] = useState<string>("");
  const [journalFilter, setJournalFilter] = useState<string>("");
  const [freeTextFilter, setFreeTextFilter] = useState("");
  const [semanticResults, setSemanticResults] = useState<Paper[] | null>(null);
  const [summaryDataByPmid, setSummaryDataByPmid] = useState<
    Record<string, { summary: string; cached: boolean }>
  >({});
  const [summarizingPmid, setSummarizingPmid] = useState<string | null>(null);

  const userLanguage = navigator.language.startsWith("de") ? "de" : "en";

  const { data: papers = [], isLoading } = useQuery({
    queryKey: ["library-papers", yearFilter, journalFilter],
    queryFn: () =>
      libraryApi.getPapers({
        year: yearFilter || undefined,
        journal: journalFilter || undefined,
        limit: 500,
        offset: 0,
      }),
  });

  const semanticSearchMutation = useMutation({
    mutationFn: (query: string) => libraryApi.semanticSearch(query, 10),
    onSuccess: (data) => setSemanticResults(data),
  });

  const deleteMutation = useMutation({
    mutationFn: (pmid: string) => libraryApi.deletePaper(pmid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library-papers"] });
      setSemanticResults(null);
    },
  });

  const bulkImportMutation = useMutation({
    mutationFn: (file: File) => libraryApi.bulkImport(file),
    onSuccess: (data) => {
      setBulkResult(data);
      queryClient.invalidateQueries({ queryKey: ["library-papers"] });
      if (data.errors.length === 0) showSuccess(`${data.imported} Papers importiert.`);
    },
    onError: (err: Error) => showError(err?.message ?? "Bulk-Import fehlgeschlagen."),
  });

  const summarizeMutation = useMutation({
    mutationFn: (pmid: string) => libraryApi.summarize(pmid, userLanguage),
    onMutate: (pmid) => setSummarizingPmid(pmid),
    onSuccess: (data, pmid) => {
      setSummaryDataByPmid((prev) => ({
        ...prev,
        [pmid]: { summary: data.summary, cached: data.cached },
      }));
    },
    onError: (err: Error) => showError(err?.message ?? "Zusammenfassung fehlgeschlagen."),
    onSettled: () => setSummarizingPmid(null),
  });

  const addPaperMutation = useMutation({
    mutationFn: (paper: {
      pmid: string;
      title: string;
      abstract: string;
      authors?: string[];
      year?: string;
      journal?: string;
      doi?: string;
      keywords?: string[];
    }) => libraryApi.addPaper(paper),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["library-papers"] });
      setAddPaperOpen(false);
      setPaperForm(initialPaperForm);
      showSuccess("Paper gespeichert und erscheint in der Bibliothek.");
    },
    onError: (err: Error) =>
      showError(err?.message ?? "Fehler beim Speichern"),
  });

  const [autoFillMessage, setAutoFillMessage] = useState<string | null>(null);
  const extractMetadataMutation = useMutation({
    mutationFn: (params: { doi?: string; pmid?: string }) =>
      libraryApi.extractMetadata({
        doi: params.doi || undefined,
        pmid: params.pmid || undefined,
      }),
    onSuccess: (data) => {
      setPaperForm((f) => ({
        ...f,
        title: data.title ?? f.title,
        authors: Array.isArray(data.authors)
          ? data.authors.join(", ")
          : f.authors,
        year: data.year != null ? String(data.year) : f.year,
        journal: data.journal ?? f.journal,
        doi: data.doi ?? f.doi,
        pmid: data.pmid ?? f.pmid,
        abstract: data.abstract ?? f.abstract,
      }));
      setAutoFillMessage("Metadaten gefunden — bitte prüfen.");
    },
    onError: (err: Error) => {
      showError(err?.message ?? "Keine Metadaten gefunden.");
    },
  });

  const handleAutoFill = useCallback(() => {
    const doi = paperForm.doi?.trim();
    const pmid = paperForm.pmid?.trim();
    if (!doi && !pmid) {
      showError("Bitte DOI oder PubMed ID eingeben.");
      return;
    }
    setAutoFillMessage(null);
    extractMetadataMutation.mutate({ doi: doi || undefined, pmid: pmid || undefined });
  }, [paperForm.doi, paperForm.pmid, showError, extractMetadataMutation]);

  const handleSemanticSearch = useCallback(() => {
    const q = semanticQuery.trim();
    if (!q) {
      setSemanticResults(null);
      return;
    }
    if (!features.semantic_search) return;
    semanticSearchMutation.mutate(q);
  }, [semanticQuery, features.semantic_search, semanticSearchMutation]);

  const displayList = semanticResults !== null ? semanticResults : papers;
  const years = useMemo(
    () =>
      Array.from(
        new Set(
          papers.map((p) => p.year).filter((y): y is string => y != null && y !== "")
        )
      ).sort((a, b) => String(b).localeCompare(String(a))),
    [papers]
  );
  const journals = useMemo(
    () =>
      Array.from(
        new Set(
          papers
            .map((p) => p.journal)
            .filter((j): j is string => j != null && j !== "")
        )
      ).sort((a, b) => a.localeCompare(b)),
    [papers]
  );

  const filteredList = useMemo(() => {
    let list = displayList;
    if (semanticResults !== null) {
      if (yearFilter)
        list = list.filter((p) => String(p.year ?? "") === yearFilter);
      if (journalFilter)
        list = list.filter((p) =>
          (p.journal ?? "").toLowerCase().includes(journalFilter.toLowerCase())
        );
    }
    if (!freeTextFilter.trim()) return list;
    const lower = freeTextFilter.toLowerCase();
    return list.filter(
      (p) =>
        (p.title ?? "").toLowerCase().includes(lower) ||
        (p.abstract ?? "").toLowerCase().includes(lower) ||
        (p.authors ?? []).some((a) => a.toLowerCase().includes(lower)) ||
        (p.journal ?? "").toLowerCase().includes(lower)
    );
  }, [
    displayList,
    freeTextFilter,
    semanticResults,
    yearFilter,
    journalFilter,
  ]);

  const handleAddPaper = () => {
    const title = paperForm.title.trim();
    const abstract = paperForm.abstract.trim();
    if (!title || !abstract) {
      showError("Titel und Abstract sind Pflichtfelder.");
      return;
    }
    const pmid = paperForm.pmid.trim() || `manual-${Date.now()}`;
    const authors = paperForm.authors
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);
    const tags = paperForm.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    addPaperMutation.mutate({
      pmid,
      title,
      abstract,
      authors: authors.length ? authors : undefined,
      year: paperForm.year.trim() || undefined,
      journal: paperForm.journal.trim() || undefined,
      doi: paperForm.doi.trim() || undefined,
      keywords: tags.length ? tags : undefined,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800">Bibliothek</h1>
        <div className="flex gap-2">
          <Button onClick={() => setAddPaperOpen(true)}>
            <Plus className="h-5 w-5" />
            Paper hinzufügen
          </Button>
          <Button variant="outline" onClick={() => setBulkImportOpen(true)}>
            <Package className="h-5 w-5" />
            Bulk Import
          </Button>
        </div>
      </div>

      {/* Semantic search */}
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-5 w-5 text-slate-400" aria-hidden />
            <textarea
              value={semanticQuery}
              onChange={(e) => setSemanticQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey))
                  handleSemanticSearch();
              }}
              placeholder="Semantische Suche — z.B.: 'Zeige Paper über BRCA1 Mutationsanalyse bei jungen Patientinnen mit familiärer Vorbelastung' oder einfach Stichwörter: 'BRCA1 therapy options'"
              className="search-textarea w-full rounded-lg border border-slate-300 py-2.5 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              rows={3}
              style={{
                resize: "vertical",
                minHeight: "80px",
                maxHeight: "200px",
                width: "100%",
              }}
              aria-label="Semantische Suche"
            />
            <small className="mt-1 block text-xs text-slate-500">
              ⌘+Enter oder Strg+Enter zum Suchen
            </small>
          </div>
          <Button
            onClick={handleSemanticSearch}
            disabled={
              !semanticQuery.trim() ||
              semanticSearchMutation.isPending ||
              !features.semantic_search
            }
            className="self-start"
          >
            <Search className="h-5 w-5" />
            Suchen
          </Button>
        </div>
        {!features.semantic_search && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            ℹ️ Demo-Version: Nur PubMed-Suche verfügbar. In der vollständigen
            Installation können Sie Papers semantisch durchsuchen.
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Jahr
          </label>
          <select
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Alle</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Journal
          </label>
          <select
            value={journalFilter}
            onChange={(e) => setJournalFilter(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm min-w-[180px]"
          >
            <option value="">Alle</option>
            {journals.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Freitext-Filter
          </label>
          <input
            type="text"
            value={freeTextFilter}
            onChange={(e) => setFreeTextFilter(e.target.value)}
            placeholder="Titel, Abstract, Autoren..."
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Paper list */}
      {isLoading ? (
        <div className="h-48 animate-pulse rounded-lg bg-slate-100" />
      ) : filteredList.length === 0 && freeTextFilter.trim() ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 py-16 text-center empty-state">
          <p className="mb-2 text-slate-600">
            Keine Papers gefunden für &quot;{freeTextFilter}&quot;
          </p>
          <Button variant="outline" onClick={() => setFreeTextFilter("")}>
            Suche zurücksetzen
          </Button>
        </div>
      ) : filteredList.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 py-16 text-center">
          <BookOpen className="mb-4 h-16 w-16 text-slate-300" />
          <p className="mb-2 text-slate-600">
            Noch keine Papers gespeichert.
          </p>
          <p className="mb-4 text-sm text-slate-500">
            Suche in Literature Mining und speichere Papers.
          </p>
          <Link to="/literature">
            <Button>Zu Literature Mining</Button>
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {semanticResults !== null && (
              <p className="mb-4 text-sm text-gray-500">
                {semanticResults.length === 0
                  ? "Keine semantisch ähnlichen Papers gefunden."
                  : `${semanticResults.length} semantisch ähnliche Papers gefunden.`}
              </p>
            )}
            {freeTextFilter.trim() && (
              <p className="text-sm text-slate-500">
                {filteredList.length} von {papers.length} Papers gefunden für
                &quot;{freeTextFilter}&quot;
              </p>
            )}
            {!freeTextFilter.trim() && (
              <p className="text-sm text-slate-600">
                {filteredList.length} Paper
                {semanticResults !== null && " (Semantische Suche)"}
              </p>
            )}
            {filteredList.map((paper) => (
              <PaperCard
                key={paper.pmid}
                paper={paper}
                summaryOverride={summaryDataByPmid[paper.pmid]?.summary}
                summaryCached={summaryDataByPmid[paper.pmid]?.cached}
                onRemove={(pmid) => deleteMutation.mutate(pmid)}
                onSummarize={features.llm_summaries ? (pmid) => summarizeMutation.mutate(pmid) : undefined}
                isRemoving={deleteMutation.isPending}
                isSummarizing={summarizingPmid === paper.pmid && summarizeMutation.isPending}
              />
            ))}
          </div>
        </>
      )}

      {/* Add paper modal */}
      <Dialog
        open={addPaperOpen}
        onOpenChange={(open) => {
          setAddPaperOpen(open);
          if (!open) setAutoFillMessage(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Paper manuell hinzufügen</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <h4 className="mb-2 text-sm font-medium text-slate-800">
                Automatisch ausfüllen
              </h4>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="text"
                  placeholder="DOI (z.B. 10.1038/...)"
                  value={paperForm.doi}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, doi: e.target.value }))
                  }
                  className="flex-1 min-w-[140px] rounded border border-slate-300 px-3 py-2 text-sm"
                />
                <span className="text-slate-500 text-sm">oder</span>
                <input
                  type="text"
                  placeholder="PubMed ID"
                  value={paperForm.pmid}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, pmid: e.target.value }))
                  }
                  className="flex-1 min-w-[120px] rounded border border-slate-300 px-3 py-2 text-sm"
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleAutoFill}
                  disabled={extractMetadataMutation.isPending}
                >
                  {extractMetadataMutation.isPending ? "…" : "🔍 Automatisch ausfüllen"}
                </Button>
              </div>
              {autoFillMessage && (
                <p className="mt-2 text-sm text-green-700">{autoFillMessage}</p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Titel *
              </label>
              <textarea
                value={paperForm.title}
                onChange={(e) =>
                  setPaperForm((f) => ({ ...f, title: e.target.value }))
                }
                placeholder="Vollständiger Paper-Titel"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                rows={2}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Autoren (kommagetrennt)
              </label>
              <input
                type="text"
                value={paperForm.authors}
                onChange={(e) =>
                  setPaperForm((f) => ({ ...f, authors: e.target.value }))
                }
                placeholder="Mustermann M, Schmidt A"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Jahr
                </label>
                <input
                  type="number"
                  value={paperForm.year}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, year: e.target.value }))
                  }
                  placeholder="2024"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Journal
                </label>
                <input
                  type="text"
                  value={paperForm.journal}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, journal: e.target.value }))
                  }
                  placeholder="Nature Genetics"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  DOI (optional)
                </label>
                <input
                  type="text"
                  value={paperForm.doi}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, doi: e.target.value }))
                  }
                  placeholder="10.1000/xyz"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  PubMed ID (optional)
                </label>
                <input
                  type="text"
                  value={paperForm.pmid}
                  onChange={(e) =>
                    setPaperForm((f) => ({ ...f, pmid: e.target.value }))
                  }
                  placeholder="Leer = automatisch"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Abstract *
              </label>
              <textarea
                value={paperForm.abstract}
                onChange={(e) =>
                  setPaperForm((f) => ({ ...f, abstract: e.target.value }))
                }
                placeholder="Vollständiger Abstract-Text"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                rows={5}
              />
              <p className="mt-1 text-xs text-slate-500">
                Abstract wird für semantische Suche verwendet.
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Tags (kommagetrennt, optional)
              </label>
              <input
                type="text"
                value={paperForm.tags}
                onChange={(e) =>
                  setPaperForm((f) => ({ ...f, tags: e.target.value }))
                }
                placeholder="BRCA1, Therapie, …"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddPaperOpen(false)}>
              Abbrechen
            </Button>
            <Button
              onClick={handleAddPaper}
              disabled={
                !paperForm.title.trim() ||
                !paperForm.abstract.trim() ||
                addPaperMutation.isPending
              }
            >
              {addPaperMutation.isPending ? "Speichern…" : "Speichern"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Import modal */}
      <Dialog
        open={bulkImportOpen}
        onOpenChange={(open) => {
          if (!open) {
            setBulkImportOpen(false);
            setBulkFile(null);
            setBulkResult(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Bulk Import</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            Importiere mehrere Papers auf einmal.
          </p>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
            <h4 className="font-medium text-slate-700">Unterstützte Formate:</h4>
            <ul className="mt-1 list-inside list-disc text-slate-600">
              <li>ZIP mit papers.json (oder einzelnen JSON-Dateien)</li>
              <li>JSON (Array von Papers)</li>
              <li>CSV (Spalten: pmid, title, abstract, authors, year, journal)</li>
            </ul>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Datei
            </label>
            <input
              type="file"
              accept=".zip,.json,.csv"
              className="w-full text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                setBulkFile(f ?? null);
                if (!f) setBulkResult(null);
              }}
            />
          </div>
          {bulkResult && (
            <div
              className={`rounded-lg border p-3 text-sm ${
                bulkResult.errors.length > 0
                  ? "border-amber-200 bg-amber-50 text-amber-900"
                  : "border-green-200 bg-green-50 text-green-900"
              }`}
            >
              <p>✅ {bulkResult.imported} Papers importiert</p>
              {bulkResult.skipped > 0 && (
                <p className="mt-1">⚠️ {bulkResult.skipped} übersprungen</p>
              )}
              {bulkResult.errors.length > 0 && (
                <div className="mt-2">
                  {bulkResult.errors.map((err, i) => (
                    <div key={i} className="text-red-700">
                      {err}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setBulkImportOpen(false);
                setBulkFile(null);
                setBulkResult(null);
              }}
            >
              Schließen
            </Button>
            <Button
              onClick={() => bulkFile && bulkImportMutation.mutate(bulkFile)}
              disabled={!bulkFile || bulkImportMutation.isPending}
            >
              {bulkImportMutation.isPending ? "⏳ Importiere…" : "📥 Importieren"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
