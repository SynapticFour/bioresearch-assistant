import { useQuery } from "@tanstack/react-query";
import { health } from "@/api/endpoints";

export interface FeatureFlags {
  embeddings: boolean;
  semantic_search: boolean;
  llm_summaries: boolean;
  spacy_ner: boolean;
  blast: boolean;
  nextflow: boolean;
}

const DEFAULT_FEATURES: FeatureFlags = {
  embeddings: false,
  semantic_search: false,
  llm_summaries: false,
  spacy_ner: false,
  blast: false,
  nextflow: false,
};

export function useFeatureFlags(): FeatureFlags {
  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: () => health.check(),
  });
  const raw = (data as { features?: FeatureFlags } | undefined)?.features;
  if (raw && typeof raw === "object") {
    return {
      embeddings: Boolean(raw.embeddings),
      semantic_search: Boolean(raw.semantic_search),
      llm_summaries: Boolean(raw.llm_summaries),
      spacy_ner: Boolean(raw.spacy_ner),
      blast: Boolean(raw.blast),
      nextflow: Boolean(raw.nextflow),
    };
  }
  return DEFAULT_FEATURES;
}
