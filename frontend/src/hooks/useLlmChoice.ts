import { useCallback, useEffect, useMemo, useState } from "react";
import { useHealth } from "@/hooks/useHealth";
import {
  getStoredLlmChoice,
  parseLlmCatalog,
  setStoredLlmChoice,
  type LlmOption,
} from "@/lib/llmChoice";

export function useLlmChoice(): {
  choiceId: string;
  setChoiceId: (id: string) => void;
  options: LlmOption[];
  defaultId: string;
} {
  const { data } = useHealth();
  const catalog = useMemo(() => parseLlmCatalog(data), [data]);
  const defaultId = catalog?.default_id ?? "";
  const options = useMemo(
    () => (catalog?.options ?? []).filter((item) => item.available),
    [catalog]
  );
  const [choiceId, setChoiceIdState] = useState(
    () => getStoredLlmChoice() ?? ""
  );

  useEffect(() => {
    if (!options.length || !defaultId) return;
    const stored = getStoredLlmChoice();
    const valid = Boolean(stored && options.some((item) => item.id === stored));
    if (!valid) {
      setStoredLlmChoice(null);
      setChoiceIdState(defaultId);
      return;
    }
    setChoiceIdState(stored as string);
  }, [defaultId, options]);

  const setChoiceId = useCallback(
    (id: string) => {
      if (!id || id === defaultId) {
        setStoredLlmChoice(null);
        setChoiceIdState(defaultId);
        return;
      }
      setStoredLlmChoice(id);
      setChoiceIdState(id);
    },
    [defaultId]
  );

  return {
    choiceId: choiceId || defaultId,
    setChoiceId,
    options,
    defaultId,
  };
}
