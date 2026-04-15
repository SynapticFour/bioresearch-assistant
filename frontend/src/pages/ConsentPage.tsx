import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, ShieldCheck } from "lucide-react";
import { consent as consentApi } from "@/api/endpoints";
import { useTranslation } from "@/hooks/useTranslation";
import { useToast } from "@/contexts/ToastContext";
import { Button } from "@/components/ui/button";

export function ConsentPage() {
  const { t } = useTranslation();
  const { showSuccess, showError } = useToast();
  const [pseudonymId, setPseudonymId] = useState("");
  const [policyVersion, setPolicyVersion] = useState("2025-1");
  const [projects, setProjects] = useState("");

  const listQuery = useQuery({
    queryKey: ["consents", pseudonymId],
    queryFn: () =>
      pseudonymId.trim()
        ? consentApi.listByPseudonym(pseudonymId.trim())
        : Promise.resolve([]),
    enabled: pseudonymId.trim().length > 0,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      consentApi.create({
        pseudonym_id: pseudonymId.trim(),
        policy_version: policyVersion.trim(),
        status: "active",
        valid_from: new Date().toISOString(),
        covered_project_ids: projects
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      showSuccess("Consent gespeichert");
      void listQuery.refetch();
    },
    onError: () => showError("Speichern fehlgeschlagen"),
  });

  return (
    <div className="flex flex-col gap-6 p-6 max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
        <ShieldCheck className="h-6 w-6" />
        {t("nav", "consentTracker")}
      </h1>
      <p className="text-sm text-slate-600">
        MII Broad Consent pro Pseudonym: erfasste Projekte bestimmen, welche
        Forschungsnutzung für den MII-Export zulässig ist.
      </p>

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
        <label className="block text-sm font-medium text-slate-700">
          Pseudonym-ID
        </label>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={pseudonymId}
          onChange={(e) => setPseudonymId(e.target.value)}
          placeholder="z. B. PP-…"
        />
        <label className="block text-sm font-medium text-slate-700">
          Policy-Version
        </label>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={policyVersion}
          onChange={(e) => setPolicyVersion(e.target.value)}
        />
        <label className="block text-sm font-medium text-slate-700">
          Abgedeckte Projekt-IDs (kommagetrennt)
        </label>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={projects}
          onChange={(e) => setProjects(e.target.value)}
          placeholder="proj-a, proj-b"
        />
        <Button
          type="button"
          disabled={!pseudonymId.trim() || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          Consent anlegen (aktiv)
        </Button>
      </div>

      {pseudonymId.trim() && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h2 className="text-sm font-semibold text-slate-800 mb-2">
            Einträge
          </h2>
          {listQuery.isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
          ) : (
            <ul className="text-sm space-y-2 font-mono">
              {(listQuery.data ?? []).map((c) => (
                <li key={c.id} className="border-b border-slate-200 pb-2">
                  <span className="text-slate-500">{c.status}</span> · v
                  {c.policy_version} · Projekte:{" "}
                  {(c.covered_project_ids as string[]).join(", ") || "—"}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
