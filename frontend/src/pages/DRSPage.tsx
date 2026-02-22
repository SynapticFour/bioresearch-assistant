import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Upload } from "lucide-react";
import { drs, type DrsObjectSummary } from "@/api/endpoints";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const TYPE_FILTER_OPTIONS = [
  { value: "all", label: "Sonstige" },
  { value: "VCF", label: "VCF" },
  { value: "FASTA", label: "FASTA" },
  { value: "BAM", label: "BAM" },
];

function getFileType(obj: DrsObjectSummary): string {
  const name = (obj.name ?? "").toLowerCase();
  if (name.endsWith(".vcf") || name.endsWith(".vcf.gz")) return "VCF";
  if (
    name.endsWith(".fasta") ||
    name.endsWith(".fa") ||
    name.endsWith(".fna")
  )
    return "FASTA";
  if (name.endsWith(".bam") || name.endsWith(".sam")) return "BAM";
  return "Sonstige";
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DRSPage() {
  const [typeFilter, setTypeFilter] = useState("all");
  const [dragOver, setDragOver] = useState(false);

  const { data: objects = [], isLoading } = useQuery({
    queryKey: ["drs-objects"],
    queryFn: () => drs.listObjects(),
  });

  const filtered = typeFilter === "all"
    ? objects
    : objects.filter((o) => getFileType(o) === typeFilter);

  const handleDownload = useCallback(
    async (obj: DrsObjectSummary) => {
      try {
        const { url } = await drs.getAccessUrl(obj.id, "default");
        const base = apiClient.defaults.baseURL ?? "";
        const fullUrl = url.startsWith("http") ? url : `${base}${url.startsWith("/") ? "" : "/"}${url}`;
        window.open(fullUrl, "_blank");
      } catch {
        window.open(
          `${apiClient.defaults.baseURL}/ga4gh/drs/v1/objects/${encodeURIComponent(obj.id)}/stream`,
          "_blank"
        );
      }
    },
    []
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">DRS Files</h1>

      <div
        className={cn(
          "rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-slate-200 bg-slate-50"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files.length) {
            // Upload API could be added later
          }
        }}
      >
        <Upload className="mx-auto mb-2 h-10 w-10 text-slate-400" />
        <p className="text-sm text-slate-600">
          Dateien hier ablegen oder klicken zum Hochladen
        </p>
        <p className="mt-1 text-xs text-slate-500">
          (Upload-API in Entwicklung)
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <label className="text-sm font-medium text-slate-700">Filter:</label>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {TYPE_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        {isLoading ? (
          <div className="p-8">
            <div className="h-32 animate-pulse rounded bg-slate-100" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            Keine Dateien gefunden
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Größe</th>
                <th className="px-4 py-3 font-medium">Typ</th>
                <th className="px-4 py-3 font-medium">Checksum</th>
                <th className="px-4 py-3 font-medium">Erstellt</th>
                <th className="px-4 py-3 font-medium">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((obj) => (
                <tr
                  key={obj.id}
                  className="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="px-4 py-2 font-medium">{obj.name ?? obj.id}</td>
                  <td className="px-4 py-2">{formatSize(obj.size)}</td>
                  <td className="px-4 py-2">{getFileType(obj)}</td>
                  <td className="px-4 py-2 font-mono text-xs text-slate-500">
                    —
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {obj.created_time
                      ? new Date(obj.created_time).toLocaleDateString("de-DE")
                      : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(obj)}
                    >
                      <Download className="h-4 w-4" />
                      Download
                    </Button>
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
