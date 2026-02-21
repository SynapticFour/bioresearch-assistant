import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronUp,
  Dna,
  Shield,
  Settings,
  Activity,
} from "lucide-react";
import {
  health,
  literature,
  pseudonymize,
  wes,
  drs,
} from "@/api/endpoints";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { AuditLogEntry } from "@/types";
import type { WesRunSummary } from "@/api/endpoints";

const HEALTH_POLL_MS = 30_000;

// --- Stats Row: 4 cards ---

function StatCard({
  title,
  value,
  sub,
  borderColor,
  loading,
}: {
  title: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  borderColor: string;
  loading?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 bg-white p-4 shadow-sm",
        "border-l-4",
        borderColor
      )}
    >
      <p className="text-sm font-medium text-slate-500">{title}</p>
      {loading ? (
        <div className="mt-1 h-8 w-16 animate-pulse rounded bg-slate-200" />
      ) : (
        <p className="mt-1 text-2xl font-semibold text-slate-800">{value}</p>
      )}
      {sub != null && (
        <div className="mt-1 text-xs text-slate-500">{sub}</div>
      )}
    </div>
  );
}

function SystemStatusCard({
  status,
  loading,
}: {
  status: "ok" | "degraded" | "error" | null;
  loading?: boolean;
}) {
  const config = {
    ok: {
      label: "Alle Systeme betriebsbereit",
      border: "border-l-green-500",
      dot: "bg-green-500",
    },
    degraded: {
      label: "Eingeschränkt",
      border: "border-l-amber-500",
      dot: "bg-amber-500",
    },
    error: {
      label: "Störung",
      border: "border-l-red-500",
      dot: "bg-red-500",
    },
  };
  const c = status ? config[status] : config.error;
  return (
    <div
      className={cn(
        "rounded-lg border border-slate-200 bg-white p-4 shadow-sm border-l-4",
        c.border
      )}
    >
      <p className="text-sm font-medium text-slate-500">System Status</p>
      {loading ? (
        <div className="mt-2 flex items-center gap-2">
          <div className="h-3 w-3 animate-pulse rounded-full bg-slate-200" />
          <div className="h-4 w-20 animate-pulse rounded bg-slate-200" />
        </div>
      ) : (
        <div className="mt-2 flex items-center gap-2">
          <span
            className={cn("h-3 w-3 rounded-full", c.dot)}
            aria-hidden
          />
          <span className="text-sm font-medium text-slate-800">{c.label}</span>
        </div>
      )}
    </div>
  );
}

// --- Middle: Timeline + Quick Actions ---

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffM = Math.floor(diffMs / 60_000);
    if (diffM < 1) return "Gerade eben";
    if (diffM < 60) return `Vor ${diffM} Min.`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `Vor ${diffH} Std.`;
    return d.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function eventLabel(entry: AuditLogEntry): string {
  if (entry.operation_type === "pseudonymize") {
    return `Pseudonymisierung (${entry.entities_count} Entitäten)`;
  }
  if (entry.operation_type === "analyze") {
    return `Analyse (${entry.entities_count} Entitäten)`;
  }
  return entry.operation_type;
}

function ActivityTimeline({
  entries,
  loading,
}: {
  entries: AuditLogEntry[];
  loading?: boolean;
}) {
  const list = entries.slice(0, 5);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        Letzte Aktivität
      </h2>
      {loading ? (
        <ul className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <li key={i} className="flex gap-3">
              <div className="h-5 w-5 shrink-0 animate-pulse rounded bg-slate-200" />
              <div className="min-w-0 flex-1">
                <div className="mb-1 h-4 w-3/4 animate-pulse rounded bg-slate-200" />
                <div className="h-3 w-16 animate-pulse rounded bg-slate-100" />
              </div>
            </li>
          ))}
        </ul>
      ) : list.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Activity className="mb-2 h-12 w-12 text-slate-300" aria-hidden />
          <p className="text-sm text-slate-500">Noch keine Daten</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {list.map((entry) => (
            <li key={entry.operation_id} className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100">
                <Shield className="h-4 w-4 text-slate-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">
                  {eventLabel(entry)}
                </p>
                <p className="text-xs text-slate-500">
                  {formatTime(entry.timestamp)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
      {!loading && entries.length > 0 && (
        <Link
          to="/audit"
          className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
        >
          Alle anzeigen
        </Link>
      )}
    </div>
  );
}

function QuickActions() {
  const actions = [
    { to: "/literature", icon: BookOpen, label: "PubMed Suche starten" },
    { to: "/pseudonymize", icon: Shield, label: "Text pseudonymisieren" },
    { to: "/workflows", icon: Settings, label: "Pipeline starten" },
    { to: "/blast", icon: Dna, label: "BLAST Suche" },
  ];
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        Quick Actions
      </h2>
      <div className="grid gap-2 sm:grid-cols-1">
        {actions.map(({ to, icon: Icon, label }) => (
          <Link
            key={to}
            to={to}
            className={cn(
              buttonVariants({ variant: "secondary", size: "lg" }),
              "h-auto w-full justify-start gap-3 py-3 text-left"
            )}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span>{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

// --- Bottom: GA4GH, Last Papers, Pipeline History ---

function GA4GHStatusCard({
  drsOk,
  wesOk,
  phenopacketsOk,
  loading,
}: {
  drsOk: boolean | null;
  wesOk: boolean | null;
  phenopacketsOk: boolean | null;
  loading?: boolean;
}) {
  const row = (label: string, ok: boolean | null) => (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-slate-700">{label}</span>
      {loading ? (
        <div className="h-4 w-4 animate-pulse rounded bg-slate-200" />
      ) : ok === true ? (
        <span className="text-green-600" aria-label={`${label} verfügbar`}>
          ✅
        </span>
      ) : ok === false ? (
        <span className="text-red-600" aria-label={`${label} nicht erreichbar`}>
          ❌
        </span>
      ) : (
        <span className="text-slate-400">—</span>
      )}
    </div>
  );
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        GA4GH Services
      </h2>
      <div className="divide-y divide-slate-100">
        {row("DRS", drsOk)}
        {row("WES", wesOk)}
        {row("Phenopackets", phenopacketsOk)}
      </div>
    </div>
  );
}

function LastPapersCard({
  papers,
  loading,
}: {
  papers: { pmid: string; title: string; year?: string | number | null }[];
  loading?: boolean;
}) {
  const list = papers.slice(0, 3);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        Letzte Paper
      </h2>
      {loading ? (
        <ul className="space-y-2">
          {[1, 2, 3].map((i) => (
            <li key={i}>
              <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
              <div className="mt-1 h-3 w-1/3 animate-pulse rounded bg-slate-100" />
            </li>
          ))}
        </ul>
      ) : list.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <BookOpen className="mb-2 h-10 w-10 text-slate-300" aria-hidden />
          <p className="text-sm text-slate-500">Noch keine Daten</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {list.map((p) => (
            <li key={p.pmid} className="truncate">
              <Link
                to={`/literature?pmid=${encodeURIComponent(p.pmid)}`}
                className="text-sm font-medium text-slate-800 hover:text-primary hover:underline"
              >
                {p.title || `PMID ${p.pmid}`}
              </Link>
              {p.year != null && (
                <span className="ml-1 text-xs text-slate-500">
                  ({String(p.year)})
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function runStateColor(state: string): string {
  const s = (state || "").toUpperCase();
  if (s === "RUNNING" || s === "INITIALIZING") return "bg-amber-100 text-amber-800 border-amber-200";
  if (s === "COMPLETE" || s === "COMPLETED") return "bg-green-100 text-green-800 border-green-200";
  if (s === "FAILED" || s === "CANCELED" || s === "CANCELLED") return "bg-red-100 text-red-800 border-red-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function PipelineHistoryCard({
  runs,
  loading,
}: {
  runs: WesRunSummary[];
  loading?: boolean;
}) {
  const list = runs.slice(0, 3);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-800">
        Pipeline History
      </h2>
      {loading ? (
        <ul className="space-y-2">
          {[1, 2, 3].map((i) => (
            <li key={i} className="flex items-center justify-between">
              <div className="h-4 w-24 animate-pulse rounded bg-slate-200 font-mono text-xs" />
              <div className="h-5 w-16 animate-pulse rounded bg-slate-200" />
            </li>
          ))}
        </ul>
      ) : list.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <Settings className="mb-2 h-10 w-10 text-slate-300" aria-hidden />
          <p className="text-sm text-slate-500">Noch keine Daten</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {list.map((run) => (
            <li
              key={run.run_id}
              className="flex items-center justify-between gap-2"
            >
              <span
                className="truncate font-mono text-xs text-slate-700"
                title={run.run_id}
              >
                {run.run_id.slice(0, 12)}…
              </span>
              <span
                className={cn(
                  "shrink-0 rounded border px-2 py-0.5 text-xs font-medium",
                  runStateColor(run.state)
                )}
              >
                {run.state}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!loading && runs.length > 0 && (
        <Link
          to="/workflows"
          className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
        >
          Alle anzeigen
        </Link>
      )}
    </div>
  );
}

export function DashboardPage() {
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
    refetchInterval: HEALTH_POLL_MS,
  });

  const { data: literatureStats, isLoading: literatureLoading } = useQuery({
    queryKey: ["literature-stats"],
    queryFn: () => literature.getStats(),
  });

  const { data: auditLog, isLoading: auditLoading } = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => pseudonymize.getAuditLog(),
  });

  const { data: wesRuns, isLoading: wesLoading } = useQuery({
    queryKey: ["wes-runs"],
    queryFn: () => wes.listRuns({ page_size: 10 }),
  });

  const {
    data: drsInfo,
    isSuccess: drsSuccess,
    isLoading: drsLoading,
  } = useQuery({
    queryKey: ["ga4gh-drs"],
    queryFn: () => drs.getServiceInfo(),
    retry: false,
  });

  const {
    data: wesInfo,
    isSuccess: wesSuccess,
    isLoading: wesInfoLoading,
  } = useQuery({
    queryKey: ["ga4gh-wes-info"],
    queryFn: () => wes.getServiceInfo(),
    retry: false,
  });

  const systemStatus: "ok" | "degraded" | "error" | null =
    healthLoading || healthData == null
      ? null
      : (healthData as { status?: string }).status === "ok"
        ? "ok"
        : "error";

  const papersCount = literatureStats?.total_papers ?? 0;
  const recentPapers = literatureStats?.recent_papers ?? [];

  const today = new Date().toISOString().slice(0, 10);
  const pseudonymizationsToday =
    auditLog?.filter(
      (e) =>
        e.operation_type === "pseudonymize" &&
        e.timestamp.startsWith(today)
    ).length ?? 0;

  const runs = wesRuns?.runs ?? [];
  const activePipelines = runs.filter(
    (r) => (r.state || "").toUpperCase() === "RUNNING"
  ).length;

  const drsOk = drsSuccess && drsInfo != null;
  const wesOk = wesSuccess && wesInfo != null;
  const phenopacketsOk = systemStatus === "ok";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>

      {/* Stats Row: 4 cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Papers gespeichert"
          value={papersCount}
          sub={
            papersCount > 0 ? (
              <span className="inline-flex items-center text-green-600">
                <ChevronUp className="h-4 w-4" /> Trend
              </span>
            ) : undefined
          }
          borderColor="border-l-blue-500"
          loading={literatureLoading}
        />
        <StatCard
          title="Pseudonymisierungen heute"
          value={pseudonymizationsToday}
          borderColor="border-l-violet-500"
          loading={auditLoading}
        />
        <StatCard
          title="Aktive Pipelines"
          value={activePipelines}
          sub={
            activePipelines > 0 ? (
              <span className="inline-flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                Läuft
              </span>
            ) : undefined
          }
          borderColor="border-l-amber-500"
          loading={wesLoading}
        />
        <SystemStatusCard status={systemStatus} loading={healthLoading} />
      </section>

      {/* Middle: Timeline (60%) + Quick Actions (40%) */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ActivityTimeline
            entries={auditLog ?? []}
            loading={auditLoading}
          />
        </div>
        <div className="lg:col-span-2">
          <QuickActions />
        </div>
      </section>

      {/* Bottom: GA4GH, Last Papers, Pipeline History */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <GA4GHStatusCard
          drsOk={drsSuccess ? drsOk : null}
          wesOk={wesSuccess ? wesOk : null}
          phenopacketsOk={phenopacketsOk}
          loading={drsLoading || wesInfoLoading}
        />
        <LastPapersCard
          papers={recentPapers.map((p) => ({
            pmid: p.pmid,
            title: p.title,
            year: p.year,
          }))}
          loading={literatureLoading}
        />
        <PipelineHistoryCard runs={runs} loading={wesLoading} />
      </section>
    </div>
  );
}
