export const LLM_CHOICE_STORAGE_KEY = "bioresearch_llm_choice";
export const LLM_CHOICE_HEADER = "X-BRA-LLM";

export interface LlmOption {
  id: string;
  backend: string;
  model: string;
  label: string;
  sovereignty: string;
  available: boolean;
  rpd?: number;
  used?: number;
  remaining?: number;
}

export interface LlmCatalog {
  default_id: string;
  header: string;
  options: LlmOption[];
}

function isLlmOption(value: unknown): value is LlmOption {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.backend === "string" &&
    typeof item.model === "string" &&
    typeof item.label === "string"
  );
}

export function parseLlmCatalog(data: unknown): LlmCatalog | null {
  if (!data || typeof data !== "object") return null;
  const llm = (data as { llm?: unknown }).llm;
  if (!llm || typeof llm !== "object") return null;
  const raw = llm as Record<string, unknown>;
  if (typeof raw.default_id !== "string" || !Array.isArray(raw.options)) {
    return null;
  }
  const options = raw.options.filter(isLlmOption).map((item) => ({
    ...item,
    available: item.available !== false,
  }));
  return {
    default_id: raw.default_id,
    header: typeof raw.header === "string" ? raw.header : LLM_CHOICE_HEADER,
    options,
  };
}

/** Prefer the server default when it is still available; else local LLM, never Sonnet/Opus. */
export function pickAvailableChoice(
  options: LlmOption[],
  defaultId: string
): string {
  if (options.some((item) => item.id === defaultId)) {
    return defaultId;
  }
  const local = options.find((item) => item.sovereignty === "full");
  if (local) return local.id;
  return options[0]?.id ?? defaultId;
}

export function getStoredLlmChoice(): string | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(LLM_CHOICE_STORAGE_KEY);
  return stored && stored.trim() ? stored : null;
}

export function setStoredLlmChoice(id: string | null): void {
  if (typeof window === "undefined") return;
  if (!id) {
    localStorage.removeItem(LLM_CHOICE_STORAGE_KEY);
    return;
  }
  localStorage.setItem(LLM_CHOICE_STORAGE_KEY, id);
}
