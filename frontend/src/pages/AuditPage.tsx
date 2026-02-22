import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown } from "lucide-react";
import { pseudonymize as pseudonymizeApi } from "@/api/endpoints";
import type { AuditLogEntry } from "@/types";
import { Button } from "@/components/ui/button";

const REFETCH_MS = 30_000;

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

function exportAuditCsv(entries: AuditLogEntry[]): void {
  const header = "Zeitstempel;Operation;Entities;Sprache;Mapping ID\n";
  const rows = entries.map(
    (e) =>
      `${formatTime(e.timestamp)};${e.operation_type};${e.entities_count};${e.language ?? "—"};${e.mapping_id ?? "—"}`
  );
  const csv = header + rows.join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-log-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function AuditPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [langFilter, setLangFilter] = useState<"all" | "de" | "en">("all");

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["audit-log"],
    queryFn: async () => {
      const data = await pseudonymizeApi.getAuditLog();
      console.log("Audit entries:", data);
      return data;
    },
    refetchInterval: REFETCH_MS,
  });

  const filtered = useMemo(() => {
    let list = entries;
    if (dateFrom) {
      const from = new Date(dateFrom);
      list = list.filter((e) => new Date(e.timestamp) >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo);
      to.setHours(23, 59, 59, 999);
      list = list.filter((e) => new Date(e.timestamp) <= to);
    }
    if (langFilter !== "all") {
      list = list.filter((e) => e.language === langFilter);
    }
    return list;
  }, [entries, dateFrom, dateTo, langFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800">Audit Log</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => exportAuditCsv(filtered)}
          disabled={filtered.length === 0}
        >
          <FileDown className="h-4 w-5" />
          Export CSV
        </Button>
      </div>

      <div className="flex flex-wrap gap-4 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Von Datum
          </label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Bis Datum
          </label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Sprache
          </label>
          <select
            value={langFilter}
            onChange={(e) =>
              setLangFilter(e.target.value as "all" | "de" | "en")
            }
            className="rounded border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="all">Alle</option>
            <option value="de">DE</option>
            <option value="en">EN</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        {isLoading ? (
          <div className="p-8">
            <div className="h-32 animate-pulse rounded bg-slate-100" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            Noch keine Pseudonymisierungen durchgeführt
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-4 py-3 font-medium">Zeitstempel</th>
                <th className="px-4 py-3 font-medium">Operation</th>
                <th className="px-4 py-3 font-medium">Entities gefunden</th>
                <th className="px-4 py-3 font-medium">Sprache</th>
                <th className="px-4 py-3 font-medium">Mapping ID</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <tr
                  key={e.operation_id}
                  className="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-2">{formatTime(e.timestamp)}</td>
                  <td className="px-4 py-2">{e.operation_type}</td>
                  <td className="px-4 py-2">{e.entities_count}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {e.language ?? "—"}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-600">
                    {e.mapping_id ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
