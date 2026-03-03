import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Dna, Plus, Search, Trash2 } from "lucide-react";
import { phenopackets, type PhenopacketCreate, type PhenopacketItem } from "@/api/endpoints";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

function extractGenes(pp: PhenopacketItem): string[] {
  try {
    const interps = (pp as { interpretations?: { diagnosis?: { genomic_interpretations?: { gene?: { symbol?: string } }[] } }[] }).interpretations ?? [];
    const genes: string[] = [];
    for (const i of interps) {
      const gi = i.diagnosis?.genomic_interpretations ?? [];
      for (const g of gi) {
        if (g.gene?.symbol) genes.push(g.gene.symbol);
      }
    }
    return [...new Set(genes)];
  } catch {
    return [];
  }
}

function extractPhenotypes(pp: PhenopacketItem): string[] {
  try {
    const pf = (pp as { phenotypic_features?: Array<{ type?: { id?: string; label?: string } }> }).phenotypic_features ?? [];
    return pf.map((p) => p.type?.id || p.type?.label || "").filter(Boolean);
  } catch {
    return [];
  }
}

function extractDiseases(pp: PhenopacketItem): string[] {
  try {
    const d = (pp as { diseases?: Array<{ term?: { id?: string; label?: string } }> }).diseases ?? [];
    return d.map((x) => x.term?.id || x.term?.label || "").filter(Boolean);
  } catch {
    return [];
  }
}

function getPseudonymId(pp: PhenopacketItem): string {
  return (pp as { id?: string }).id ?? (pp as { subject?: { id?: string } }).subject?.id ?? "";
}

interface TagsInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  label?: string;
}

function TagsInput({ value, onChange, placeholder, label }: TagsInputProps) {
  const [input, setInput] = useState("");
  const add = () => {
    const t = input.trim();
    if (t && !value.includes(t)) onChange([...value, t]);
    setInput("");
  };
  return (
    <div>
      {label && (
        <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      )}
      <div className="flex flex-wrap gap-2 rounded-lg border border-slate-300 bg-white p-2">
        {value.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="cursor-pointer"
            onClick={() => onChange(value.filter((x) => x !== tag))}
          >
            {tag} ×
          </Badge>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={placeholder}
          className="min-w-[120px] flex-1 border-0 bg-transparent p-1 text-sm outline-none"
        />
        <Button type="button" variant="ghost" size="sm" onClick={add}>
          Hinzufügen
        </Button>
      </div>
    </div>
  );
}

export function PhenopacketsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [createStep, setCreateStep] = useState<1 | 2 | 3>(1);
  const [clinicalText, setClinicalText] = useState("");
  const [detailItem, setDetailItem] = useState<PhenopacketItem | null>(null);
  const [form, setForm] = useState<PhenopacketCreate>({
    pseudonym_id: "",
    phenotypes: [],
    diseases: [],
    genes_of_interest: [],
    notes: "",
  });

  const { data: list = [], isLoading } = useQuery({
    queryKey: ["phenopackets"],
    queryFn: () => phenopackets.list(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: PhenopacketCreate) => phenopackets.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phenopackets"] });
      setCreateOpen(false);
      setCreateStep(1);
      setClinicalText("");
      setForm({
        pseudonym_id: "",
        phenotypes: [],
        diseases: [],
        genes_of_interest: [],
        notes: "",
      });
      showSuccess("Phenopacket erstellt");
    },
    onError: (err: Error) => showError(err?.message ?? "Fehler beim Erstellen"),
  });

  const extractMutation = useMutation({
    mutationFn: (text: string) => phenopackets.extractFromText(text),
    onSuccess: (data) => {
      const phenotypes = (data.terms ?? []).map((t) => t.hpo_id || t.name);
      const genes = data.genes ?? [];
      setForm((f) => ({
        ...f,
        phenotypes: [...new Set([...(f.phenotypes ?? []), ...phenotypes])],
        genes_of_interest: [...new Set([...(f.genes_of_interest ?? []), ...genes])],
      }));
      setCreateStep(2);
    },
    onError: (err: Error) => showError(err?.message ?? "Extraktion fehlgeschlagen"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => phenopackets.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["phenopackets"] });
      setDetailItem(null);
      showSuccess("Phenopacket gelöscht");
    },
    onError: (err: Error) => showError(err?.message ?? "Fehler beim Löschen"),
  });

  const handleCreate = useCallback(() => {
    if (!form.pseudonym_id.trim()) {
      showError("Pseudonym ID ist Pflichtfeld");
      return;
    }
    createMutation.mutate({
      ...form,
      pseudonym_id: form.pseudonym_id.trim(),
      phenotypes: form.phenotypes?.length ? form.phenotypes : undefined,
      diseases: form.diseases?.length ? form.diseases : undefined,
      genes_of_interest: form.genes_of_interest?.length ? form.genes_of_interest : undefined,
    });
  }, [form, createMutation, showError]);


  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800">Phenopackets</h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-5 w-5" />
          Neues Phenopacket
        </Button>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <span className="font-medium">🔒 DSGVO-Hinweis:</span> Alle Daten werden pseudonymisiert
        gespeichert. Verwenden Sie ausschließlich Pseudonym-IDs — niemals echte Patientennamen.
      </div>

      {isLoading ? (
        <div className="h-48 animate-pulse rounded-lg bg-slate-100" />
      ) : list.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 py-16 text-center">
          <Dna className="mb-4 h-16 w-16 text-slate-300" />
          <p className="mb-2 text-slate-600">Noch keine Phenopackets.</p>
          <Button onClick={() => setCreateOpen(true)}>Neues Phenopacket anlegen</Button>
        </div>
      ) : (
        <div className="space-y-2">
          {list.map((pp) => {
            const id = getPseudonymId(pp);
            const genes = extractGenes(pp);
            const phenotypes = extractPhenotypes(pp);
            const diseases = extractDiseases(pp);
            return (
              <div
                key={id}
                className="flex cursor-pointer flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-primary/30"
                onClick={() => setDetailItem(pp)}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-800">{id}</p>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {genes.length > 0 && (
                      <span className="text-xs text-slate-500">
                        Gene: {genes.join(", ")}
                      </span>
                    )}
                    {phenotypes.length > 0 && (
                      <span className="text-xs text-slate-500">
                        HPO: {phenotypes.slice(0, 3).join(", ")}
                        {phenotypes.length > 3 && " …"}
                      </span>
                    )}
                    {diseases.length > 0 && (
                      <span className="text-xs text-slate-500">
                        OMIM/Erkrankungen: {diseases.slice(0, 2).join(", ")}
                      </span>
                    )}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    const genes = extractGenes(pp);
                    const phenotypes = extractPhenotypes(pp);
                    const diseases = extractDiseases(pp);
                    const allTerms = [...genes, ...phenotypes, ...diseases].filter(Boolean);
                    const searchTerm = allTerms.length ? allTerms.join(" ") : getPseudonymId(pp);
                    navigate(`/literature?q=${encodeURIComponent(searchTerm)}`);
                  }}
                >
                  <Search className="h-4 w-4" />
                  In Literature Mining suchen
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDetailItem(pp);
                  }}
                >
                  Details
                </Button>
              </div>
            );
          })}
        </div>
      )}

      {/* Create modal — 3 steps */}
      <Dialog
        open={createOpen}
        onOpenChange={(open) => {
          if (!open) {
            setCreateStep(1);
            setClinicalText("");
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Neues Phenopacket</DialogTitle>
          </DialogHeader>
          <div className="mb-3 flex gap-2 rounded-lg border border-slate-200 p-1">
            <button
              type="button"
              onClick={() => setCreateStep(1)}
              className={`flex-1 rounded px-2 py-1.5 text-sm font-medium ${createStep === 1 ? "bg-primary text-primary-foreground" : "text-slate-600"}`}
            >
              1. Text
            </button>
            <button
              type="button"
              onClick={() => setCreateStep(2)}
              className={`flex-1 rounded px-2 py-1.5 text-sm font-medium ${createStep === 2 ? "bg-primary text-primary-foreground" : "text-slate-600"}`}
            >
              2. Prüfen
            </button>
            <button
              type="button"
              onClick={() => setCreateStep(3)}
              className={`flex-1 rounded px-2 py-1.5 text-sm font-medium ${createStep === 3 ? "bg-primary text-primary-foreground" : "text-slate-600"}`}
            >
              3. Speichern
            </button>
          </div>
          <div className="space-y-4">
            {createStep === 1 && (
              <>
                <p className="text-sm text-slate-600">
                  Geben Sie eine klinische Beschreibung ein (nur pseudonymisierte Daten). Das System extrahiert Phänotypen und Gene.
                </p>
                <textarea
                  value={clinicalText}
                  onChange={(e) => setClinicalText(e.target.value)}
                  placeholder="z.B. Patient zeigt rezidivierende Krampfanfälle seit dem 3. Lebensjahr. Familienanamnese positiv für BRCA1-Mutation..."
                  rows={6}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <Button
                  onClick={() => extractMutation.mutate(clinicalText)}
                  disabled={!clinicalText.trim() || extractMutation.isPending}
                >
                  {extractMutation.isPending ? "…" : "🧬 Automatisch analysieren"}
                </Button>
              </>
            )}
            {createStep === 2 && (
              <>
                <TagsInput
                  label="Gene of Interest"
                  value={form.genes_of_interest ?? []}
                  onChange={(tags) => setForm((f) => ({ ...f, genes_of_interest: tags }))}
                  placeholder="z.B. BRCA1"
                />
                <TagsInput
                  label="HPO Phänotypen"
                  value={form.phenotypes ?? []}
                  onChange={(tags) => setForm((f) => ({ ...f, phenotypes: tags }))}
                  placeholder="z.B. HP:0001250"
                />
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setCreateStep(1)}>Zurück</Button>
                  <Button onClick={() => setCreateStep(3)}>Weiter → Speichern</Button>
                </div>
              </>
            )}
            {createStep === 3 && (
              <>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Pseudonym ID (Pflichtfeld) *
                  </label>
                  <input
                    type="text"
                    value={form.pseudonym_id}
                    onChange={(e) => setForm((f) => ({ ...f, pseudonym_id: e.target.value }))}
                    placeholder="z.B. PATIENT-2024-001"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                  <p className="mt-1 text-xs text-amber-700">
                    🔒 Vergeben Sie eine nicht-identifizierende ID. Niemals echte Namen!
                  </p>
                </div>
                <DialogFooter>
                  {!form.pseudonym_id.trim() && (
                    <p className="text-sm text-amber-600 mb-2 w-full basis-full">
                      ⚠️ Bitte Pseudonym-ID eingeben.
                    </p>
                  )}
                  {(form.phenotypes?.length ?? 0) === 0 && (
                    <p className="text-sm text-amber-600 mb-2 w-full basis-full">
                      ⚠️ Bitte mindestens einen Phänotyp in Schritt 2 auswählen.
                    </p>
                  )}
                  <Button variant="outline" onClick={() => setCreateStep(2)}>Zurück</Button>
                  <Button
                    onClick={() => handleCreate()}
                    disabled={
                      !form.pseudonym_id.trim() ||
                      (form.phenotypes?.length ?? 0) === 0 ||
                      createMutation.isPending
                    }
                  >
                    {createMutation.isPending ? "…" : "💾 Phenopacket speichern"}
                  </Button>
                </DialogFooter>
              </>
            )}
          </div>
          {createStep !== 3 && (
            <div className="flex gap-2 border-t pt-3">
              <Button variant="outline" onClick={() => setCreateOpen(false)}>Abbrechen</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Detail modal */}
      <Dialog open={!!detailItem} onOpenChange={(open) => !open && setDetailItem(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          {detailItem && (
            <>
              <DialogHeader>
                <DialogTitle>{getPseudonymId(detailItem)}</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-medium text-slate-700">Gene:</span>{" "}
                  {extractGenes(detailItem).join(", ") || "—"}
                </div>
                <div>
                  <span className="font-medium text-slate-700">HPO Phänotypen:</span>{" "}
                  {extractPhenotypes(detailItem).join(", ") || "—"}
                </div>
                <div>
                  <span className="font-medium text-slate-700">Erkrankungen:</span>{" "}
                  {extractDiseases(detailItem).join(", ") || "—"}
                </div>
                <pre className="max-h-48 overflow-auto rounded bg-slate-100 p-2 text-xs">
                  {JSON.stringify(detailItem, null, 2)}
                </pre>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    const genes = extractGenes(detailItem);
                    const phenotypes = extractPhenotypes(detailItem)
                      .map((t) =>
                        t.includes(":")
                          ? t.split(":").slice(1).join(":")  // HP:0001234 → Label bevorzugen
                          : t
                      );
                    const diseases = extractDiseases(detailItem);
                    const allTerms = [...genes, ...phenotypes, ...diseases].filter(Boolean);
                    const searchTerm = allTerms.length ? allTerms.join(" ") : getPseudonymId(detailItem);
                    setDetailItem(null);
                    navigate(`/literature?q=${encodeURIComponent(searchTerm)}`);
                  }}
                >
                  <Search className="h-4 w-4" />
                  In Literature Mining suchen
                </Button>
                <Button
                  variant="outline"
                  className="text-red-600"
                  onClick={() => {
                    if (window.confirm("Phenopacket wirklich löschen?"))
                      deleteMutation.mutate(getPseudonymId(detailItem));
                  }}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                  Löschen
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
