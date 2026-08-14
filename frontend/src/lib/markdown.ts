import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: true });

/** Render Markdown to HTML and strip script/event-handler XSS. */
export function renderMarkdownSafe(markdown: string): string {
  if (!markdown) return "";
  const raw = marked.parse(markdown, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "iframe", "object", "embed", "form"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"],
  });
}
