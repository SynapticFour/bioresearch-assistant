import { cn } from "@/lib/utils";
import { useTranslation } from "@/hooks/useTranslation";
import { useLlmChoice } from "@/hooks/useLlmChoice";

interface LlmChoiceSelectProps {
  className?: string;
}

export function LlmChoiceSelect({ className }: LlmChoiceSelectProps) {
  const { t } = useTranslation();
  const { choiceId, setChoiceId, options, defaultId } = useLlmChoice();

  if (!options.length) {
    return null;
  }

  return (
    <label className={cn("flex items-center gap-2", className)}>
      <span className="hidden text-xs font-medium text-muted sm:inline">
        {t("llm", "label")}
      </span>
      <select
        value={choiceId}
        onChange={(event) => setChoiceId(event.target.value)}
        aria-label={t("llm", "aria")}
        className="max-w-[220px] rounded-lg border border-slate-300 bg-surface px-2 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.id === defaultId
              ? `${option.label} · ${t("llm", "serverDefault")}`
              : option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
