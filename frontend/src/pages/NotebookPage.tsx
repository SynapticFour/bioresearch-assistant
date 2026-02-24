import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { marked } from "marked";
import { notebooks as notebooksApi } from "@/api/endpoints";
import type { NotebookItem } from "@/api/endpoints";
import { useTranslation } from "@/hooks/useTranslation";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const DEBOUNCE_MS = 2000;

export default function NotebookPage() {
  const { t } = useTranslation();
  const { showSuccess, showError } = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tagFilter, setTagFilter] = useState("");

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ["notebooks", { search, tag: tagFilter, skip: 0, limit: 50 }],
    queryFn: () =>
      notebooksApi.list({ search: search || undefined, tag: tagFilter || undefined, limit: 50 }),
  });

  const notebooks = listData?.items ?? [];
  const selected = notebooks.find((n) => n.id === selectedId) ?? null;

  const createMutation = useMutation({
    mutationFn: () => notebooksApi.create({ title: "Neues Notizbuch", content: "", tags: [] }),
    onSuccess: (nb) => {
      queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      setSelectedId(nb.id);
      showSuccess("Notizbuch erstellt");
    },
    onError: () => showError("Fehler beim Erstellen"),
  });

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">{t("nav", "notebooks")}</h1>
      </div>
      <div className="grid flex-1 grid-cols-12 gap-4 overflow-hidden">
        {/* Left: list */}
        <div className="col-span-3 flex flex-col gap-2 overflow-hidden rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          <div className="flex gap-2">
            <Input
              placeholder="Suchen..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9"
            />
            <Button
              size="icon"
              variant="outline"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              aria-label="Neues Notizbuch"
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            </Button>
          </div>
          {listLoading ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <ul className="flex-1 overflow-y-auto space-y-1">
              {notebooks.length === 0 && (
                <li className="py-4 text-center text-sm text-slate-500">Keine Notizbücher</li>
              )}
              {notebooks.map((nb) => (
                <li key={nb.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(nb.id)}
                    className={cn(
                      "w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                      selectedId === nb.id
                        ? "bg-primary text-primary-foreground"
                        : "bg-slate-50 text-slate-800 hover:bg-slate-100"
                    )}
                  >
                    <span className="truncate block">{nb.title || "Ohne Titel"}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Center: editor */}
        <div className="col-span-6 flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          {selected ? (
            <NotebookEditor
              notebook={selected}
              onSelectChange={setSelectedId}
              onSaved={() => queryClient.invalidateQueries({ queryKey: ["notebooks"] })}
              showSuccess={showSuccess}
              showError={showError}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center text-slate-500">
              Notizbuch auswählen oder neu erstellen
            </div>
          )}
        </div>

        {/* Right: linked resources + AI */}
        <div className="col-span-3 flex flex-col gap-3 overflow-hidden">
          {selected && (
            <>
              <LinkedResources notebook={selected} onLink={() => queryClient.invalidateQueries({ queryKey: ["notebooks"] })} />
              <AIAssistPanel notebook={selected} onUpdated={() => queryClient.invalidateQueries({ queryKey: ["notebooks"] })} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function NotebookEditor({
  notebook,
  onSelectChange,
  onSaved,
  showSuccess,
  showError,
}: {
  notebook: NotebookItem;
  onSelectChange: (id: string | null) => void;
  onSaved: () => void;
  showSuccess: (msg: string) => void;
  showError: (msg: string) => void;
}) {
  const [title, setTitle] = useState(notebook.title);
  const [content, setContent] = useState(notebook.content);
  const [showPreview, setShowPreview] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    setTitle(notebook.title);
    setContent(notebook.content);
  }, [notebook.id, notebook.title, notebook.content]);

  const updateMutation = useMutation({
    mutationFn: (payload: { title?: string; content?: string }) =>
      notebooksApi.update(notebook.id, payload),
    onMutate: () => setSaveStatus("saving"),
    onSuccess: () => {
      setSaveStatus("saved");
      onSaved();
      queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      setTimeout(() => setSaveStatus("idle"), 2000);
    },
    onError: () => {
      setSaveStatus("idle");
      showError("Speichern fehlgeschlagen");
    },
  });

  const scheduleSave = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      debounceRef.current = null;
      updateMutation.mutate({ title, content });
    }, DEBOUNCE_MS);
  }, [title, content, updateMutation]);

  useEffect(() => {
    if (title !== notebook.title || content !== notebook.content) scheduleSave();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [title, content, scheduleSave, notebook.title, notebook.content]);

  const deleteMutation = useMutation({
    mutationFn: () => notebooksApi.delete(notebook.id),
    onSuccess: () => {
      onSelectChange(null);
      queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      showSuccess("Notizbuch gelöscht");
    },
    onError: () => showError("Löschen fehlgeschlagen"),
  });

  const html = useMemo(() => (content ? marked(content) : ""), [content]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="min-w-0 flex-1 rounded border-0 bg-transparent text-lg font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-primary"
          placeholder="Titel"
        />
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {saveStatus === "saving" && "Speichert..."}
            {saveStatus === "saved" && "Gespeichert ✓"}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowPreview((p) => !p)}
          >
            {showPreview ? "Editor" : "Vorschau"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={async () => {
              const blob = await notebooksApi.export(notebook.id, "md");
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${notebook.title || "notebook"}.md`;
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => deleteMutation.mutate()}
            disabled={deleteMutation.isPending}
            aria-label="Löschen"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden p-3">
        {showPreview ? (
          <div
            className="prose prose-sm max-w-none overflow-y-auto rounded border border-slate-100 bg-slate-50/50 p-3"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="h-full w-full resize-none rounded border border-slate-200 p-3 font-mono text-sm text-slate-800 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="Markdown-Inhalt..."
            spellCheck="false"
          />
        )}
      </div>
    </div>
  );
}

function LinkedResources({
  notebook,
  onLink,
}: {
  notebook: NotebookItem;
  onLink: () => void;
}) {
  const [linkType, setLinkType] = useState<"paper" | "drs" | "phenopacket">("paper");
  const [linkId, setLinkId] = useState("");
  const linkMutation = useMutation({
    mutationFn: () => notebooksApi.link(notebook.id, linkType, linkId),
    onSuccess: () => {
      onLink();
      setLinkId("");
    },
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-slate-800">Verknüpfte Ressourcen</h3>
      <div className="space-y-2 text-xs">
        {notebook.linked_pmids.length > 0 && (
          <div>
            <span className="font-medium text-slate-600">Papers</span>
            <ul className="mt-1 space-y-0.5">
              {notebook.linked_pmids.map((pmid) => (
                <li key={pmid}>
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    PMID {pmid}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        {notebook.linked_drs_ids.length > 0 && (
          <div>
            <span className="font-medium text-slate-600">DRS</span>
            <ul className="mt-1 space-y-0.5">
              {notebook.linked_drs_ids.map((id) => (
                <li key={id} className="truncate font-mono text-slate-600">
                  {id}
                </li>
              ))}
            </ul>
          </div>
        )}
        {notebook.linked_phenopacket_ids.length > 0 && (
          <div>
            <span className="font-medium text-slate-600">Phenopackets</span>
            <ul className="mt-1 space-y-0.5">
              {notebook.linked_phenopacket_ids.map((id) => (
                <li key={id} className="font-mono text-slate-600">{id}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <select
          value={linkType}
          onChange={(e) => setLinkType(e.target.value as "paper" | "drs" | "phenopacket")}
          className="rounded border border-slate-200 px-2 py-1 text-sm"
        >
          <option value="paper">Paper (PMID)</option>
          <option value="drs">DRS</option>
          <option value="phenopacket">Phenopacket</option>
        </select>
        <input
          type="text"
          value={linkId}
          onChange={(e) => setLinkId(e.target.value)}
          placeholder={linkType === "paper" ? "PMID" : "ID"}
          className="min-w-0 flex-1 rounded border border-slate-200 px-2 py-1 text-sm"
        />
        <Button
          size="sm"
          onClick={() => linkMutation.mutate()}
          disabled={!linkId.trim() || linkMutation.isPending}
        >
          Verknüpfen
        </Button>
      </div>
    </div>
  );
}

function AIAssistPanel({
  notebook,
  onUpdated,
}: {
  notebook: NotebookItem;
  onUpdated: () => void;
}) {
  const [mode, setMode] = useState<"summary" | "next_steps" | "both">("both");
  const assistMutation = useMutation({
    mutationFn: () => notebooksApi.aiAssist(notebook.id, mode),
    onSuccess: () => {
      onUpdated();
    },
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
        <Sparkles className="h-4 w-4" />
        KI Assistent
      </h3>
      <div className="space-y-2 text-sm">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as "summary" | "next_steps" | "both")}
          className="w-full rounded border border-slate-200 px-2 py-1.5"
        >
          <option value="summary">Zusammenfassung</option>
          <option value="next_steps">Nächste Schritte</option>
          <option value="both">Beides</option>
        </select>
        <Button
          className="w-full"
          size="sm"
          onClick={() => assistMutation.mutate()}
          disabled={assistMutation.isPending || !notebook.content.trim()}
        >
          {assistMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Generieren"
          )}
        </Button>
        {notebook.ai_summary && (
          <div className="rounded bg-slate-50 p-2">
            <p className="font-medium text-slate-600">Zusammenfassung</p>
            <p className="mt-1 text-slate-700">{notebook.ai_summary}</p>
          </div>
        )}
        {notebook.ai_next_steps && (
          <div className="rounded bg-slate-50 p-2">
            <p className="font-medium text-slate-600">Nächste Schritte</p>
            <p className="mt-1 whitespace-pre-wrap text-slate-700">{notebook.ai_next_steps}</p>
          </div>
        )}
      </div>
    </div>
  );
}
