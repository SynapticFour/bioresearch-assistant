import { describe, expect, it } from "vitest";
import { parseLlmCatalog } from "./llmChoice";

describe("parseLlmCatalog", () => {
  it("reads options from a health payload", () => {
    const catalog = parseLlmCatalog({
      llm: {
        default_id: "ollama:mistral:7b",
        header: "X-BRA-LLM",
        options: [
          {
            id: "ollama:mistral:7b",
            backend: "ollama",
            model: "mistral:7b",
            label: "Ollama (mistral:7b)",
            sovereignty: "full",
            available: true,
          },
        ],
      },
    });
    expect(catalog?.default_id).toBe("ollama:mistral:7b");
    expect(catalog?.options).toHaveLength(1);
  });

  it("returns null when llm is missing", () => {
    expect(parseLlmCatalog({ status: "healthy" })).toBeNull();
  });
});
