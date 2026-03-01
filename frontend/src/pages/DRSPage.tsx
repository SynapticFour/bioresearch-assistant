import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Download, Upload, Plus, Copy, Settings } from "lucide-react";
import { drs, type DrsObjectSummary } from "@/api/endpoints";
import { apiClient } from "@/api/client";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

const TYPE_FILTER_OPTIONS = [
  { value: "all", label: "Sonstige" },
  { value: "VCF", label: "VCF" },
  { value: "FASTA", label: "FASTA" },
  { value: "BAM", label: "BAM" },
  { value: "FASTQ", label: "FASTQ" },
  { value: "BED", label: "BED" },
];

const FILE_TYPE_OPTIONS = [
  { value: "VCF", label: "VCF" },
  { value: "FASTA", label: "FASTA" },
  { value: "BAM", label: "BAM" },
  { value: "FASTQ", label: "FASTQ" },
  { value: "BED", label: "BED" },
  { value: "Sonstige", label: "Sonstige" },
];

const ACCEPT_FILES = ".vcf,.vcf.gz,.fasta,.fa,.fna,.bam,.sam,.fastq,.fastq.gz,.bed";

function getFileType(obj: DrsObjectSummary): string {
  const name = (obj.name ?? obj.id ?? "").toLowerCase();
  if (name.endsWith(".vcf") || name.endsWith(".vcf.gz")) return "VCF";
  if (
    name.endsWith(".fasta") ||
    name.endsWith(".fa") ||
    name.endsWith(".fna")
  )
    return "FASTA";
  if (name.endsWith(".bam") || name.endsWith(".sam")) return "BAM";
  if (name.endsWith(".fastq") || name.endsWith(".fastq.gz")) return "FASTQ";
  if (name.endsWith(".bed")) return "BED";
  return "Sonstige";
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getDrsUri(objectId: string): string {
  const base = apiClient.defaults.baseURL ?? "";
  const host = base.replace(/^https?:\/\//, "").replace(/\/.*$/, "") || "localhost";
  return `drs://${host}/${objectId}`;
}

export function DRSPage() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [typeFilter, setTypeFilter] = useState("all");
  const [dragOver, setDragOver] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registerName, setRegisterName] = useState("");
  const [registerDesc, setRegisterDesc] = useState("");
  const [registerFileType, setRegisterFileType] = useState("VCF");
  const [registerPath, setRegisterPath] = useState("");
  const [registerServerPath, setRegisterServerPath] = useState("");
  const [registerFile, setRegisterFile] = useState<File | null>(null);
  const [uploads, setUploads] = useState<
    { name: string; status: "uploading" | "success" | "error"; drsId?: string; error?: string }[]
  >([]);

  const { data: objects = [], isLoading } = useQuery({
    queryKey: ["drs-objects"],
    queryFn: () => drs.listObjects(),
  });

  const registerMutation = useMutation({
    mutationFn: (form: FormData) => drs.registerObject(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drs-objects"] });
      setRegisterOpen(false);
      setRegisterName("");
      setRegisterDesc("");
      setRegisterPath("");
      setRegisterServerPath("");
      setRegisterFile(null);
      showSuccess("Datei registriert. DRS ID und Zugriffs-URL sind verfügbar.");
    },
    onError: (err: Error) =>
      showError(err?.message ?? "Fehler beim Registrieren"),
  });

  const filtered = typeFilter === "all"
    ? objects
    : objects.filter((o) => getFileType(o) === typeFilter);

  const registerFileDirect = useCallback(
    async (file: File) => {
      setUploads((prev) => [...prev, { name: file.name, status: "uploading" }]);
      const form = new FormData();
      form.append("name", file.name);
      form.append("description", "");
      form.append("file", file);
      try {
        const drsObject = await drs.registerObject(form);
        setUploads((prev) =>
          prev.map((u) =>
            u.name === file.name
              ? { ...u, status: "success" as const, drsId: drsObject.id }
              : u
          )
        );
        await queryClient.invalidateQueries({ queryKey: ["drs-objects"] });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setUploads((prev) =>
          prev.map((u) =>
            u.name === file.name ? { ...u, status: "error" as const, error: message } : u
          )
        );
      }
    },
    [queryClient]
  );

  const handleRegister = () => {
    const name = registerName.trim();
    if (!name) {
      showError("Name ist Pflichtfeld.");
      return;
    }
    const form = new FormData();
    form.append("name", name);
    if (registerDesc.trim()) form.append("description", registerDesc.trim());
    if (registerServerPath.trim()) {
      form.append("server_path", registerServerPath.trim());
    } else if (registerPath.trim()) {
      form.append("path", registerPath.trim());
    } else if (registerFile) {
      form.append("file", registerFile);
    } else {
      showError("Bitte Datei hochladen oder Pfad angeben.");
      return;
    }
    registerMutation.mutate(form);
  };

  const handleCopyUri = useCallback((obj: DrsObjectSummary) => {
    const uri = getDrsUri(obj.id);
    void navigator.clipboard.writeText(uri).then(() => showSuccess("DRS URI kopiert"));
  }, [showSuccess]);

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
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800">DRS Files</h1>
        <Button onClick={() => setRegisterOpen(true)}>
          <Plus className="h-5 w-5" />
          Datei registrieren
        </Button>
      </div>

      <div
        className={cn(
          "rounded-lg border-2 border-dashed p-6 text-center transition-colors",
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
          const files = Array.from(e.dataTransfer.files);
          if (files.length) {
            files.forEach((file) => void registerFileDirect(file));
          }
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT_FILES}
          className="hidden"
          onChange={(e) => {
            const fileList = e.target.files;
            if (fileList?.length) {
              Array.from(fileList).forEach((f) => void registerFileDirect(f));
              e.target.value = "";
            }
          }}
        />
        <Upload className="mx-auto mb-2 h-10 w-10 text-slate-400" />
        <p className="text-sm text-slate-600">
          Dateien hier ablegen oder klicken zum Hochladen
        </p>
        <p className="text-xs text-slate-500">
          VCF, FASTA, BAM, FASTQ, BED — auch .gz
        </p>
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((u) => (
            <div
              key={u.name}
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                u.status === "success"
                  ? "border-green-200 bg-green-50"
                  : u.status === "error"
                    ? "border-red-200 bg-red-50"
                    : "border-slate-200 bg-slate-50"
              }`}
            >
              <span className="font-medium">{u.name}</span>
              {u.status === "uploading" && <span className="text-slate-500">⏳ Lädt…</span>}
              {u.status === "success" && (
                <span className="text-green-700">✅ {u.drsId}</span>
              )}
              {u.status === "error" && (
                <span className="text-red-700">❌ {u.error}</span>
              )}
            </div>
          ))}
        </div>
      )}

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
                <th className="px-4 py-3 font-medium">DRS ID</th>
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
                    {obj.id}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {obj.created_time
                      ? new Date(obj.created_time).toLocaleDateString("de-DE")
                      : "—"}
                  </td>
                  <td className="px-4 py-2 flex flex-wrap gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopyUri(obj)}
                    >
                      <Copy className="h-4 w-4" />
                      Kopieren
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(obj)}
                    >
                      <Download className="h-4 w-4" />
                      Download
                    </Button>
                    <Link to="/workflows" state={{ drsUri: getDrsUri(obj.id) }}>
                      <Button variant="ghost" size="sm">
                        <Settings className="h-4 w-4" />
                        In Pipeline
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Register modal */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Datei registrieren</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Name *
              </label>
              <input
                type="text"
                value={registerName}
                onChange={(e) => setRegisterName(e.target.value)}
                placeholder="z.B. patient001.vcf"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Beschreibung
              </label>
              <textarea
                value={registerDesc}
                onChange={(e) => setRegisterDesc(e.target.value)}
                placeholder="Optionale Beschreibung"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                rows={2}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Dateityp
              </label>
              <select
                value={registerFileType}
                onChange={(e) => setRegisterFileType(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {FILE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Datei hochladen
              </label>
              <input
                type="file"
                accept={ACCEPT_FILES}
                className="w-full text-sm"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  setRegisterFile(f ?? null);
                  if (f) setRegisterName(f.name);
                }}
              />
              <p className="mt-1 text-xs text-slate-500">
                Erlaubt: .vcf, .fasta, .fa, .bam, .fastq, .bed
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Oder: Relativer Pfad (unter DRS-Speicher)
              </label>
              <input
                type="text"
                value={registerPath}
                onChange={(e) => setRegisterPath(e.target.value)}
                placeholder="z.B. data/sample.vcf"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Oder: Server-Pfad (große Dateien &gt;500MB)
              </label>
              <input
                type="text"
                value={registerServerPath}
                onChange={(e) => setRegisterServerPath(e.target.value)}
                placeholder="/data/genomics/meine-datei.bam"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <p className="mt-1 text-xs text-slate-500">
                Datei muss unter DRS-Speicher liegen. Max. Upload direkt: 500MB.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRegisterOpen(false)}>
              Abbrechen
            </Button>
            <Button
              onClick={handleRegister}
              disabled={
                !registerName.trim() ||
                (!registerFile && !registerPath.trim() && !registerServerPath.trim()) ||
                registerMutation.isPending
              }
            >
              {registerMutation.isPending ? "Registrieren…" : "Registrieren"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
