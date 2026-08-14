import { describe, expect, it } from "vitest";
import { renderMarkdownSafe } from "./markdown";

describe("renderMarkdownSafe", () => {
  it("renders markdown emphasis", () => {
    expect(renderMarkdownSafe("**bold**")).toContain("<strong>");
  });

  it("strips script tags from untrusted markdown", () => {
    const html = renderMarkdownSafe('<script>alert(1)</script>ok');
    expect(html.toLowerCase()).not.toContain("<script");
    expect(html).toContain("ok");
  });

  it("strips javascript: urls", () => {
    const html = renderMarkdownSafe("[x](javascript:alert(1))");
    expect(html.toLowerCase()).not.toContain("javascript:");
  });
});
