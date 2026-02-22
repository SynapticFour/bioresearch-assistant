import { useState, useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Play, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import { blast } from "@/api/endpoints";
import type { BlastHit } from "@/types";
import { Button } from "@/components/ui/button";

const POLL_MS = 5_000;

export function BlastPage() {
  const [sequence, setSequence] = useState("");
  const [database, setDatabase] = useState("nt");
  const [evalue, setEvalue] = useState("0.001");
  const [runId, setRunId] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: async () => {
      const res = await blast.search(sequence.trim(), database, {
        evalue: parseFloat(evalue) || 0.001,
      });
      return res.run_id;
    },
    onSuccess: (id) => setRunId(id),
  });

  const resultsQuery = useQuery({
    queryKey: ["blast-results", runId],
    queryFn: () => blast.getResults(runId!, { papers: true }),
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data?.results?.hits?.length && runId) return POLL_MS;
      return false;
    },
  });

  const handleStart = useCallback(() => {
    if (!sequence.trim()) return;
    startMutation.mutate();
  }, [sequence, startMutation]);

  const hits = resultsQuery.data?.results?.hits ?? [];
  const isLoading = startMutation.isPending || (!!runId && resultsQuery.isLoading);

  return (
    <div className="flex h-full min-h-0 gap-0">
      <aside className="flex w-[400px] shrink-0 flex-col gap-4 border-r border-slate-200 bg-white p-6">
        <h1 className="text-xl font-semibold text-slate-800">BLAST Suche</h1>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Sequence
          </label>
          <textarea
            value={sequence}
            onChange={(e) => setSequence(e.target.value)}
            placeholder="ATCG..."
            rows={10}
            className="w-full rounded-lg border border-slate-300 p-3 font-mono text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Datenbank
          </label>
          <select
            value={database}
            onChange={(e) => setDatabase(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
          >
            <option value="nt">nt</option>
            <option value="nr">nr</option>
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
            value={evalue}
            onChange={(e) => setEvalue(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </div>
        <Button
          onClick={handleStart}
          disabled={!sequence.trim() || isLoading}
          className="w-full"
        >
          <Play className="h-5 w-5" />
          BLAST starten
        </Button>
      </aside>

      <div className="min-w-0 flex-1 overflow-auto p-6">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Ergebnisse</h2>
        {isLoading && !hits.length && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-slate-500">
            Job läuft… (Polling alle 5s)
          </div>
        )}
        {!runId && !isLoading && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-slate-500">
            Bitte Sequence eingeben und BLAST starten.
          </div>
        )}
        {hits.length > 0 && (
          <div className="space-y-2">
            {hits.map((hit) => (
              <HitRow key={hit.hit_id} hit={hit} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HitRow({ hit }: { hit: BlastHit }) {
  const [expanded, setExpanded] = useState(false);
  const topHsp = hit.hsps?.[0];
  const score = topHsp?.score ?? 0;
  const expectVal = topHsp?.expect ?? 0;
  const identity =
    topHsp && topHsp.identities != null && topHsp.align_length
      ? Math.round((topHsp.identities / topHsp.align_length) * 100)
      : null;

  const searchTerm = hit.hit_def?.slice(0, 50) ?? hit.hit_id;

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div
        className="flex cursor-pointer items-center gap-4 p-4"
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setExpanded((x) => !x)}
      >
        <span className="min-w-0 flex-1 truncate font-medium text-slate-800">
          {hit.hit_def ?? hit.hit_id}
        </span>
        <span className="shrink-0 text-sm text-slate-600">{score}</span>
        <span className="shrink-0 text-sm text-slate-600">{expectVal}</span>
        <span className="shrink-0 text-sm text-slate-600">
          {identity != null ? `${identity} %` : "—"}
        </span>
        <Link
          to={`/literature?q=${encodeURIComponent(searchTerm)}`}
          onClick={(e) => e.stopPropagation()}
        >
          <Button variant="ghost" size="sm">
            <BookOpen className="h-4 w-4" />
            Paper zu diesem Gen suchen
          </Button>
        </Link>
        {expanded ? (
          <ChevronUp className="h-5 w-5 shrink-0" />
        ) : (
          <ChevronDown className="h-5 w-5 shrink-0" />
        )}
      </div>
      {expanded && hit.hsps && hit.hsps.length > 0 && (
        <div className="border-t border-slate-100 bg-slate-50 p-4">
          <h4 className="mb-2 text-sm font-medium text-slate-700">HSP Details</h4>
          <pre className="overflow-auto rounded bg-white p-2 font-mono text-xs">
            {hit.hsps.map((hsp, i) => (
              <div key={i}>
                Score: {hsp.score} E-value: {hsp.expect} Identity: {hsp.identities}
                /{hsp.align_length}
                {hsp.query && `\nQuery: ${hsp.query}`}
                {hsp.match && `\nMatch: ${hsp.match}`}
                {hsp.hit && `\nHit: ${hsp.hit}`}
              </div>
            ))}
          </pre>
        </div>
      )}
    </div>
  );
}
