export type NbCell = {
  cell_type: string;
  source?: string | string[];
  outputs?: unknown[];
  execution_count?: number | null;
  metadata?: Record<string, unknown>;
};

export type NbDocument = {
  nbformat: number;
  nbformat_minor?: number;
  metadata?: Record<string, unknown>;
  cells: NbCell[];
};

export function sourceToString(source: string | string[] | undefined): string {
  if (!source) return "";
  return Array.isArray(source) ? source.join("") : source;
}

export function stringToSource(text: string): string[] {
  if (!text) return [""];
  const lines = text.split("\n");
  return lines.map((line, i) => (i === lines.length - 1 ? line : `${line}\n`));
}

export function parseNotebook(content: string): NbDocument {
  const data = JSON.parse(content) as NbDocument;
  if (data.nbformat !== 4 || !Array.isArray(data.cells)) {
    throw new Error("Not a nbformat v4 notebook");
  }
  return data;
}

export function stringifyNotebook(nb: NbDocument): string {
  return JSON.stringify(nb, null, 2);
}
