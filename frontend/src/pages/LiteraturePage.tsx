import { useState, useCallback, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import {
  Search,
  ExternalLink,
  BookOpen,
  FileDown,
  ChevronDown,
  ChevronUp,
  Sparkles,
  FlaskConical,
  ListChecks,
} from "lucide-react";
import { literature } from "@/api/endpoints";
import type { Paper } from "@/types";
import { useToast } from "@/contexts/ToastContext";
import { useTranslation } from "@/hooks/useTranslation";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SEARCH_HISTORY_KEY = "literature-search-history";
const MAX_HISTORY = 5;
const SUGGESTIONS = ["BRCA1", "COVID-19 treatment", "CRISPR"];
const PUBMED_URL = (pmid: string) =>
  `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;

function loadSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as unknown;
    return Array.isArray(arr) && arr.every((x) => typeof x === "string")
      ? arr.slice(0, MAX_HISTORY)
      : [];
  } catch {
    return [];
  }
}

function saveSearchToHistory(query: string): void {
  const prev = loadSearchHistory().filter((q) => q !== query);
  const next = [query, ...prev].slice(0, MAX_HISTORY);
  localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(next));
}

// --- Left panel: search form ---

interface SearchFormProps {
  query: string;
  setQuery: (q: string) => void;
  maxResults: number;
  setMaxResults: (n: number) => void;
  language: "de" | "en";
  setLanguage: (l: "de" | "en") => void;
  onSearch: () => void;
  isSearching: boolean;
  history: string[];
  onHistoryClick: (q: string) => void;
  searchLabel: string;
  semanticSearchAvailable: boolean;
}

function SearchForm({
  query,
  setQuery,
  maxResults,
  setMaxResults,
  language,
  setLanguage,
  onSearch,
  isSearching,
  history,
  onHistoryClick,
  searchLabel,
  semanticSearchAvailable,
}: SearchFormProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="relative">
        <Search className="absolute left-3 top-3 h-5 w-5 text-slate-400" aria-hidden />
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onSearch();
          }}
          placeholder="Semantische Suche — z.B.: 'Zeige Paper über BRCA1 Mutationsanalyse bei jungen Patientinnen mit familiärer Vorbelastung' oder einfach Stichwörter: 'BRCA1 therapy options'"
          className="search-textarea w-full rounded-lg border border-slate-300 py-3 pl-10 pr-4 text-slate-800 placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          rows={3}
          style={{
            resize: "vertical",
            minHeight: "80px",
            maxHeight: "200px",
            width: "100%",
          }}
          aria-label="Suchbegriff"
        />
        <small className="mt-1 block text-xs text-slate-500">
          ⌘+Enter oder Strg+Enter zum Suchen
        </small>
      </div>
      {semanticSearchAvailable ? (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-600">
            🔍 PubMed: Keyword-Suche
          </span>
          <span className="rounded-full bg-green-100 px-2 py-1 text-green-700">
            🧠 Bibliothek: Semantische Suche
          </span>
        </div>
      ) : (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          ℹ️ Demo-Version: Nur PubMed-Suche verfügbar. In der vollständigen
          Installation werden zusätzlich Ihre Papers semantisch durchsucht.
        </div>
      )}
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Max Ergebnisse
        </label>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={5}
            max={50}
            step={5}
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            className="flex-1 accent-primary"
            aria-label="Maximale Anzahl Ergebnisse"
          />
          <span className="w-8 text-sm font-medium text-slate-700">
            {maxResults}
          </span>
        </div>
      </div>
      <div>
        <span className="mb-1 block text-sm font-medium text-slate-700">
          Sprache
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
      <Button
        onClick={onSearch}
        disabled={!query.trim() || isSearching}
        className="w-full"
        size="lg"
      >
        {isSearching ? (
          <>
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
            {searchLabel}…
          </>
        ) : (
          <>
            <Search className="h-5 w-5" />
            {searchLabel}
          </>
        )}
      </Button>
      {history.length > 0 && (
        <div>
          <span className="mb-2 block text-sm font-medium text-slate-600">
            Suchverlauf
          </span>
          <div className="flex flex-wrap gap-2">
            {history.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => onHistoryClick(q)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-400"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// --- Right panel: empty / loading / results ---

function EmptyState({ onSuggestionClick }: { onSuggestionClick: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <BookOpen className="mb-4 h-16 w-16 text-slate-300" aria-hidden />
      <p className="mb-2 text-lg font-medium text-slate-600">
        Gib einen Suchbegriff ein
      </p>
      <p className="mb-4 text-sm text-slate-500">
        Vorschläge:
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onSuggestionClick(s)}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function SkeletonCards() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div className="mb-2 h-5 w-3/4 animate-pulse rounded bg-slate-200" />
          <div className="mb-2 h-4 w-1/2 animate-pulse rounded bg-slate-100" />
          <div className="space-y-1">
            <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

function exportPapersCsv(papers: Paper[], query: string): void {
  const header = "PMID,Title,Authors,Year,Journal,Abstract,Summary\n";
  const escape = (s: string) =>
    `"${String(s ?? "").replace(/"/g, '""')}"`;
  const rows = papers.map(
    (p) =>
      [
        p.pmid,
        p.title,
        (p.authors ?? []).join("; "),
        p.year ?? "",
        p.journal ?? "",
        (p.abstract ?? "").replace(/\s+/g, " "),
        (p.summary ?? "").replace(/\s+/g, " "),
      ].map(escape).join(",")
  );
  const csv = header + rows.join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `literature-${query.slice(0, 30).replace(/\W/g, "-")}-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// --- Paper card (expandable abstract, summary box, tags, footer) ---

interface PaperCardProps {
  paper: Paper;
  onTitleClick: () => void;
  onSave?: (paper: Paper) => void;
  isSaving?: boolean;
  saveLabel?: string;
}

function PaperCard({
  paper,
  onTitleClick,
  onSave,
  isSaving,
  saveLabel = "Speichern",
}: PaperCardProps) {
  const [abstractExpanded, setAbstractExpanded] = useState(false);
  const abstract = paper.abstract ?? "";
  const lineClamp = abstractExpanded ? undefined : 3;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-2">
        <button
          type="button"
          onClick={onTitleClick}
          className="text-left text-base font-bold text-slate-800 hover:text-primary hover:underline"
        >
          {paper.title || `PMID ${paper.pmid}`}
        </button>
      </h3>
      <p className="mb-2 text-sm text-slate-500">
        {(paper.authors ?? []).slice(0, 5).join(", ")}
        {(paper.authors?.length ?? 0) > 5 && " et al."}
        {paper.year != null && ` · ${paper.year}`}
        {paper.journal && ` · ${paper.journal}`}
        {paper.score != null && (
          <span className="ml-2 text-teal-600">
            Relevanz: {(paper.score * 100).toFixed(0)}%
          </span>
        )}
      </p>
      {abstract && (
        <div className="mb-3">
          <p
            className="text-sm text-slate-700"
            style={
              lineClamp
                ? { display: "-webkit-box", WebkitLineClamp: lineClamp, WebkitBoxOrient: "vertical" as const, overflow: "hidden" }
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
                <>Weniger <ChevronUp className="h-4 w-4" /></>
              ) : (
                <>Mehr <ChevronDown className="h-4 w-4" /></>
              )}
            </button>
          )}
        </div>
      )}
      {paper.summary && (
        <div className="mb-3 rounded-lg bg-teal-50 p-3 text-sm text-slate-800 border border-teal-100">
          <span className="font-medium text-teal-800">KI-Zusammenfassung</span>
          <p className="mt-1">{paper.summary}</p>
        </div>
      )}
      {(paper.keywords?.length ?? 0) > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {paper.keywords!.map((kw) => (
            <Badge key={kw} variant="secondary" className="text-xs">
              {kw}
            </Badge>
          ))}
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
          PubMed öffnen
          <ExternalLink className="h-4 w-4" />
        </a>
        {onSave && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => onSave(paper)}
            disabled={isSaving}
          >
            {saveLabel}
          </Button>
        )}
      </footer>
    </article>
  );
}

// --- Paper detail modal ---

interface PaperDetailModalProps {
  paper: Paper | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSimilarSearch: (query: string) => void;
  onSave?: (paper: Paper) => void;
  isSaving?: boolean;
  saveLabel?: string;
}

function PaperDetailModal({
  paper,
  open,
  onOpenChange,
  onSimilarSearch,
  onSave,
  isSaving,
  saveLabel = "Speichern",
}: PaperDetailModalProps) {
  if (!paper) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="pr-8">{paper.title || `PMID ${paper.pmid}`}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            {(paper.authors ?? []).join(", ")}
            {paper.year != null && ` · ${paper.year}`}
            {paper.journal && ` · ${paper.journal}`}
          </p>
          {paper.abstract && (
            <div>
              <h4 className="mb-1 text-sm font-semibold text-slate-700">Abstract</h4>
              <p className="text-sm text-slate-700 whitespace-pre-wrap">{paper.abstract}</p>
            </div>
          )}
          {paper.summary && (
            <div>
              <h4 className="mb-1 text-sm font-semibold text-slate-700">KI-Zusammenfassung</h4>
              <p className="text-sm text-slate-700">{paper.summary}</p>
            </div>
          )}
          {(paper.key_findings?.length ?? 0) > 0 && (
            <div>
              <h4 className="mb-1 flex items-center gap-1 text-sm font-semibold text-slate-700">
                <ListChecks className="h-4 w-4" /> Key Findings
              </h4>
              <ul className="list-inside list-disc text-sm text-slate-700">
                {paper.key_findings!.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {(paper.methods?.length ?? 0) > 0 && (
            <div>
              <h4 className="mb-1 flex items-center gap-1 text-sm font-semibold text-slate-700">
                <FlaskConical className="h-4 w-4" /> Methods
              </h4>
              <ul className="list-inside list-disc text-sm text-slate-700">
                {paper.methods!.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          {onSave && (
            <Button
              variant="ghost"
              onClick={() => onSave(paper)}
              disabled={isSaving}
            >
              {saveLabel}
            </Button>
          )}
          <Button
            variant="outline"
            onClick={() => onSimilarSearch(paper.title || paper.pmid)}
          >
            <Sparkles className="h-4 w-4" />
            Ähnliche Paper finden
          </Button>
          <Link
            to="/workflows"
            className={buttonVariants({ variant: "default" })}
          >
            In Pipeline nutzen
          </Link>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- Main page ---

export function LiteraturePage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const features = useFeatureFlags();
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(20);
  const { language, changeLanguage, t } = useTranslation();
  const [history, setHistory] = useState<string[]>(loadSearchHistory);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [queryWarning, setQueryWarning] = useState<{
    show: boolean;
    types: string[];
    message: string;
  }>({ show: false, types: [], message: "" });
  const { showSuccess, showError } = useToast();

  const mutation = useMutation({
    mutationFn: async ({
      q,
      max,
      lang,
    }: {
      q: string;
      max: number;
      lang?: string;
    }) => literature.search(q, max, lang ?? "de"),
  });

  const saveMutation = useMutation({
    mutationFn: (paper: Paper) => literature.savePaper(paper),
    onSuccess: () => showSuccess("Paper gespeichert"),
    onError: (err: Error) =>
      showError(err?.message ?? "Fehler beim Speichern"),
  });

  const papers = mutation.data?.papers ?? [];
  const hasSearched = mutation.isSuccess || mutation.isPending;
  const isLoading = mutation.isPending;
  const error = mutation.error;

  const runSearch = useCallback(() => {
    const q = query.trim();
    if (!q) return;
    saveSearchToHistory(q);
    setHistory(loadSearchHistory());
    mutation.mutate({ q, max: maxResults, lang: language });
  }, [query, maxResults, language, mutation]);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    try {
      const validation = await literature.validateQuery(q, language);
      if (!validation.safe && validation.detected_types?.length) {
        setQueryWarning({
          show: true,
          types: validation.detected_types ?? [],
          message: validation.warning ?? "Mögliche sensitive Daten erkannt.",
        });
        return;
      }
    } catch {
      // Bei Fehler der Validierung trotzdem suchen lassen
    }
    runSearch();
  }, [query, language, runSearch]);

  // URL ?q= prefills search and starts it (e.g. from Phenopackets "Literature search mit…")
  useEffect(() => {
    const q = searchParams.get("q");
    if (q && q.trim()) {
      setQuery(q);
      saveSearchToHistory(q);
      setHistory(loadSearchHistory());
      mutation.mutate({ q: q.trim(), max: maxResults, lang: language });
    }
  }, [searchParams]);

  useEffect(() => {
    const searchQuery = (location.state as { searchQuery?: string } | null)?.searchQuery;
    if (searchQuery && typeof searchQuery === "string") {
      setQuery(searchQuery);
      saveSearchToHistory(searchQuery);
      setHistory(loadSearchHistory());
      mutation.mutate({ q: searchQuery, max: maxResults, lang: language });
    }
  }, [location.state]);

  const handleHistoryClick = useCallback((q: string) => {
    setQuery(q);
    saveSearchToHistory(q);
    setHistory(loadSearchHistory());
    mutation.mutate({ q, max: maxResults, lang: language });
  }, [maxResults, language, mutation]);

  const handleSuggestionClick = useCallback((q: string) => {
    setQuery(q);
    saveSearchToHistory(q);
    setHistory(loadSearchHistory());
    mutation.mutate({ q, max: maxResults, lang: language });
  }, [maxResults, language, mutation]);

  const handleSimilarSearch = useCallback((q: string) => {
    setModalOpen(false);
    setSelectedPaper(null);
    setQuery(q);
    saveSearchToHistory(q);
    setHistory(loadSearchHistory());
    mutation.mutate({ q, max: maxResults, lang: language });
  }, [maxResults, language, mutation]);

  return (
    <div className="flex min-h-0 flex-1 gap-0 overflow-hidden">
      {/* Left panel: 400px fixed */}
      <aside className="flex w-[400px] shrink-0 flex-col border-r border-slate-200 bg-white p-6">
        <h1 className="mb-6 text-xl font-semibold text-slate-800">
          {t("literature", "title")}
        </h1>
        <SearchForm
          query={query}
          setQuery={setQuery}
          maxResults={maxResults}
          setMaxResults={setMaxResults}
          language={language}
          setLanguage={changeLanguage}
          onSearch={handleSearch}
          isSearching={isLoading}
          history={history}
          onHistoryClick={handleHistoryClick}
          searchLabel={t("literature", "search")}
          semanticSearchAvailable={features.semantic_search}
        />
      </aside>

      {/* Right panel: flex, scroll */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-slate-50">
        <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
          {!hasSearched && <EmptyState onSuggestionClick={handleSuggestionClick} />}
          {isLoading && <SkeletonCards />}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              Suche fehlgeschlagen. Bitte später erneut versuchen.
            </div>
          )}
          {hasSearched && !isLoading && papers.length > 0 && (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-slate-700">
                    {papers.length} Paper gefunden für &quot;{query.trim()}&quot;
                  </p>
                  {features.semantic_search ? (
                    <span className="rounded bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-800">
                      🧠 Semantische Suche aktiv
                    </span>
                  ) : (
                    <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
                      🔍 Keyword-Suche
                    </span>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportPapersCsv(papers, query)}
                >
                  <FileDown className="h-4 w-4" />
                  Export CSV
                </Button>
              </div>
              <div className="space-y-4">
                {papers.map((paper) => (
                  <PaperCard
                    key={paper.pmid}
                    paper={paper}
                    onTitleClick={() => {
                      setSelectedPaper(paper);
                      setModalOpen(true);
                    }}
                    onSave={(p) => saveMutation.mutate(p)}
                    isSaving={saveMutation.isPending}
                    saveLabel={t("literature", "save")}
                  />
                ))}
              </div>
            </>
          )}
          {hasSearched && !isLoading && papers.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookOpen className="mb-4 h-16 w-16 text-slate-300" />
              <p className="text-slate-600">{t("literature", "noResults")}</p>
            </div>
          )}
        </div>
      </div>

      <PaperDetailModal
        paper={selectedPaper}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSimilarSearch={handleSimilarSearch}
        onSave={(p) => saveMutation.mutate(p)}
        isSaving={saveMutation.isPending}
        saveLabel={t("literature", "save")}
      />

      {queryWarning.show && (
        <Dialog open={queryWarning.show} onOpenChange={(open) => !open && setQueryWarning((w) => ({ ...w, show: false }))}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-amber-700">
                ⚠️ Mögliche sensitive Daten erkannt
              </DialogTitle>
            </DialogHeader>
            <p className="text-sm text-slate-700">{queryWarning.message}</p>
            <p className="text-xs text-slate-600">
              Erkannte Typen: {queryWarning.types.join(", ")}
            </p>
            <p className="text-xs text-slate-600">
              Suchanfragen werden an PubMed (extern) gesendet. Bitte stellen Sie sicher, dass keine Patientendaten enthalten sind.
            </p>
            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setQueryWarning((w) => ({ ...w, show: false }))}
              >
                Anfrage überarbeiten
              </Button>
              <Button
                className="bg-amber-600 hover:bg-amber-700"
                onClick={() => {
                  setQueryWarning((w) => ({ ...w, show: false }));
                  runSearch();
                }}
              >
                Trotzdem suchen
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
