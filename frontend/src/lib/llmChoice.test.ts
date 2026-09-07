import { describe, expect, it } from "vitest";
import { parseLlmCatalog, pickAvailableChoice, type LlmOption } from "./llmChoice";

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

  it("keeps Haiku rpd fields from health", () => {
    const catalog = parseLlmCatalog({
      llm: {
        default_id: "ollama:mistral:7b",
        header: "X-BRA-LLM",
        options: [
          {
            id: "anthropic:claude-haiku-4-5",
            backend: "anthropic",
            model: "claude-haiku-4-5",
            label: "Claude Haiku (Cloud)",
            sovereignty: "partial",
            available: false,
            rpd: 25,
            used: 25,
            remaining: 0,
          },
        ],
      },
    });
    expect(catalog?.options[0]?.rpd).toBe(25);
    expect(catalog?.options[0]?.remaining).toBe(0);
    expect(catalog?.options[0]?.available).toBe(false);
  });
});

describe("pickAvailableChoice", () => {
  const ollama: LlmOption = {
    id: "ollama:mistral:7b",
    backend: "ollama",
    model: "mistral:7b",
    label: "Ollama",
    sovereignty: "full",
    available: true,
  };
  const haiku: LlmOption = {
    id: "anthropic:claude-haiku-4-5",
    backend: "anthropic",
    model: "claude-haiku-4-5",
    label: "Haiku",
    sovereignty: "partial",
    available: true,
    rpd: 25,
  };
  const sonnet: LlmOption = {
    id: "anthropic:claude-sonnet-5",
    backend: "anthropic",
    model: "claude-sonnet-5",
    label: "Sonnet",
    sovereignty: "partial",
    available: true,
  };

  it("keeps the server default when it is still available", () => {
    expect(pickAvailableChoice([haiku, ollama], haiku.id)).toBe(haiku.id);
  });

  it("falls back to local LLM when Haiku is exhausted, not Sonnet", () => {
    expect(
      pickAvailableChoice(
        [ollama, { ...haiku, available: false }, sonnet].filter((o) => o.available),
        haiku.id
      )
    ).toBe(ollama.id);
  });
});
