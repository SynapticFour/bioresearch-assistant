import { describe, expect, it } from "vitest";
import { parseNotebook, sourceToString, stringifyNotebook, stringToSource } from "./ipynb";

describe("ipynb helpers", () => {
  it("round-trips a nbformat v4 notebook", () => {
    const raw = JSON.stringify({
      nbformat: 4,
      nbformat_minor: 5,
      metadata: {},
      cells: [{ cell_type: "code", source: ["print(1)\n"], outputs: [], execution_count: null }],
    });
    const nb = parseNotebook(raw);
    expect(sourceToString(nb.cells[0].source)).toContain("print(1)");
    expect(stringifyNotebook(nb)).toContain("nbformat");
  });

  it("rejects non-v4 notebooks", () => {
    expect(() => parseNotebook(JSON.stringify({ nbformat: 3, cells: [] }))).toThrow();
  });

  it("splits source into notebook line arrays", () => {
    expect(stringToSource("a\nb")).toEqual(["a\n", "b"]);
  });
});
