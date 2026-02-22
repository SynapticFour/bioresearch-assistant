import { useState, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Trash2,
  Search,
} from "lucide-react";
import { library as libraryApi } from "@/api/endpoints";
import { useHealth } from "@/hooks/useHealth";
import type { Paper } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const PUBMED_URL = (pmid: string) =>
  `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;

function useIsRailway(): boolean {
  const { data } = useHealth();
  const deployment = (data?.deployment as string) ?? "";
  return deployment === "railway";
}

interface PaperCardProps {
  paper: Paper;
  onRemove: (pmid: string) => void;
  isRemoving: boolean;
}

function PaperCard({ paper, onRemove, isRemoving }: PaperCardProps) {
  const [abstractExpanded, setAbstractExpanded] = useState(false);
  const abstract = paper.abstract ?? "";
  const lineClamp = abstractExpanded ? undefined : 3;

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

export function LibraryPage() {
  const queryClient = useQueryClient();
  const isRailway = useIsRailway();

  const [semanticQuery, setSemanticQuery] = useState("");
  const [yearFilter, setYearFilter] = useState<string>("");
  const [journalFilter, setJournalFilter] = useState<string>("");
  const [freeTextFilter, setFreeTextFilter] = useState("");
  const [semanticResults, setSemanticResults] = useState<Paper[] | null>(null);

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

  const handleSemanticSearch = useCallback(() => {
    const q = semanticQuery.trim();
    if (!q) {
      setSemanticResults(null);
      return;
    }
    if (isRailway) return;
    semanticSearchMutation.mutate(q);
  }, [semanticQuery, isRailway, semanticSearchMutation]);

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">Bibliothek</h1>

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
            disabled={!semanticQuery.trim() || semanticSearchMutation.isPending}
            className="self-start"
          >
            <Search className="h-5 w-5" />
            Suchen
          </Button>
        </div>
        {isRailway && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Semantische Suche ist in der Demo-Version nicht verfügbar. In der
            vollständigen Installation können Sie Papers semantisch durchsuchen.
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
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            {filteredList.length} Paper
            {semanticResults !== null && " (Semantische Suche)"}
          </p>
          {filteredList.map((paper) => (
            <PaperCard
              key={paper.pmid}
              paper={paper}
              onRemove={(pmid) => deleteMutation.mutate(pmid)}
              isRemoving={deleteMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}
