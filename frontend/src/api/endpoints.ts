/**
 * API endpoint functions for BioResearch Assistant.
 * Uses apiClient (axios) with baseURL from VITE_API_URL.
 */

import { apiClient } from "./client";
import type {
  Paper,
  PseudonymizeResult,
  AuditLogEntry,
  BlastResult,
  DRSObject,
} from "@/types";

const API_V1 = "/api/v1";
const WES_PREFIX = "/ga4gh/wes/v1";
const DRS_PREFIX = "/ga4gh/drs/v1";

// ----- Literature (Phase 1 – endpoints may be added later) -----

export interface LiteratureStats {
  total_papers: number;
  recent_papers: Paper[];
}

export interface ValidateQueryResponse {
  safe: boolean;
  warning?: string;
  detected_types: string[];
  recommendation?: string;
}

export const literature = {
  async validateQuery(
    query: string,
    language: string = "de"
  ): Promise<ValidateQueryResponse> {
    const { data } = await apiClient.post<ValidateQueryResponse>(
      `${API_V1}/literature/search/validate-query`,
      { query, language }
    );
    return data;
  },
  async getStats(): Promise<LiteratureStats> {
    const { data } = await apiClient.get<LiteratureStats>(
      `${API_V1}/literature/stats`
    );
    return data;
  },
  async search(
    query: string,
    maxResults: number = 20,
    language: string = "de"
  ): Promise<{ papers: Paper[] }> {
    const { data } = await apiClient.post<Paper[] | { papers: Paper[] }>(
      `${API_V1}/literature/search`,
      { query, max_results: maxResults, language }
    );
    const papers = Array.isArray(data) ? data : (data?.papers ?? []);
    return { papers };
  },
  async getPaper(id: string): Promise<Paper> {
    const { data } = await apiClient.get<Paper>(
      `${API_V1}/literature/papers/${encodeURIComponent(id)}`
    );
    return data;
  },
  async savePaper(paper: {
    pmid: string;
    title?: string | null;
    abstract?: string | null;
    authors?: string[];
    year?: string | number | null;
    journal?: string | null;
    doi?: string | null;
    keywords?: string[];
    summary?: string | null;
  }): Promise<Paper> {
    const year =
      paper.year != null && paper.year !== undefined
        ? String(paper.year)
        : null;
    const body = {
      pmid: paper.pmid,
      title: paper.title ?? "",
      abstract: paper.abstract ?? "",
      authors: Array.isArray(paper.authors) ? paper.authors : [],
      year,
      journal: paper.journal ?? "",
      doi: paper.doi ?? null,
      keywords: Array.isArray(paper.keywords) ? paper.keywords : [],
      summary: paper.summary ?? null,
    };
    const { data } = await apiClient.post<Paper>(
      `${API_V1}/literature/papers`,
      body
    );
    return data;
  },
};

// ----- Library (saved papers) -----

export const library = {
  async addPaper(paper: {
    pmid: string;
    title: string;
    abstract: string;
    authors?: string[];
    year?: string | number | null;
    journal?: string | null;
    doi?: string | null;
    keywords?: string[];
  }): Promise<Paper> {
    const year =
      paper.year != null && paper.year !== undefined
        ? String(paper.year)
        : undefined;
    const { data } = await apiClient.post<Paper>(`${API_V1}/library/papers`, {
      pmid: paper.pmid,
      title: paper.title,
      abstract: paper.abstract,
      authors: Array.isArray(paper.authors) ? paper.authors : [],
      year: year ?? undefined,
      journal: paper.journal ?? undefined,
      doi: paper.doi ?? undefined,
      keywords: Array.isArray(paper.keywords) ? paper.keywords : [],
    });
    return data;
  },
  async getPapers(params?: {
    year?: string | null;
    journal?: string | null;
    limit?: number;
    offset?: number;
  }): Promise<Paper[]> {
    const searchParams = new URLSearchParams();
    if (params?.year) searchParams.set("year", params.year);
    if (params?.journal) searchParams.set("journal", params.journal);
    if (params?.limit != null) searchParams.set("limit", String(params.limit));
    if (params?.offset != null) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    const url = `${API_V1}/library/papers${qs ? `?${qs}` : ""}`;
    const { data } = await apiClient.get<Paper[]>(url);
    return data;
  },
  async deletePaper(pmid: string): Promise<void> {
    await apiClient.delete(`${API_V1}/library/papers/${encodeURIComponent(pmid)}`);
  },
  async semanticSearch(
    query: string,
    limit: number = 10,
    threshold: number = 1.0
  ): Promise<Paper[]> {
    const { data } = await apiClient.post<Paper[]>(
      `${API_V1}/library/search/semantic`,
      { query, limit, threshold }
    );
    return data;
  },
  async bulkImport(file: File): Promise<{ imported: number; skipped: number; errors: string[] }> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await apiClient.post<{
      imported: number;
      skipped: number;
      errors: string[];
    }>(`${API_V1}/library/bulk-import`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
  async summarize(
    pmid: string,
    language = "de"
  ): Promise<{ summary: string; cached: boolean; language: string }> {
    const { data } = await apiClient.post<{
      summary: string;
      cached: boolean;
      language: string;
    }>(`${API_V1}/library/summarize`, { pmid, language });
    return data;
  },
  async extractMetadata(params: {
    doi?: string | null;
    pmid?: string | null;
    text?: string | null;
  }): Promise<{
    title?: string;
    authors?: string[];
    year?: number | null;
    journal?: string;
    doi?: string | null;
    abstract?: string;
    pmid?: string;
    source?: string;
  }> {
    const { data } = await apiClient.post<Record<string, unknown>>(
      `${API_V1}/library/extract-metadata`,
      {
        doi: params.doi ?? undefined,
        pmid: params.pmid ?? undefined,
        text: params.text ?? undefined,
      }
    );
    return data as {
      title?: string;
      authors?: string[];
      year?: number | null;
      journal?: string;
      doi?: string | null;
      abstract?: string;
      pmid?: string;
      source?: string;
    };
  },
};

// ----- Pseudonymize -----

export const pseudonymize = {
  async analyze(
    text: string,
    language: string = "de"
  ): Promise<{ entities_found: PseudonymizeResult["entities_found"] }> {
    const { data } = await apiClient.post<PseudonymizeResult>(
      `${API_V1}/pseudonymize`,
      { text, language }
    );
    return { entities_found: data.entities_found };
  },
  async pseudonymize(
    text: string,
    language: string = "de"
  ): Promise<PseudonymizeResult> {
    const { data } = await apiClient.post<PseudonymizeResult>(
      `${API_V1}/pseudonymize`,
      { text, language }
    );
    return data;
  },
  async getAuditLog(): Promise<AuditLogEntry[]> {
    const { data } = await apiClient.get<AuditLogEntry[]>(
      `${API_V1}/pseudonymize/audit-log`
    );
    return data;
  },
  async reverse(mappingId: string): Promise<{
    mapping_id: string;
    original_text: string;
    pseudonymized_text: string;
    accessed_by: string;
    access_time: string;
  }> {
    const { data } = await apiClient.post<{
      mapping_id: string;
      original_text: string;
      pseudonymized_text: string;
      accessed_by: string;
      access_time: string;
    }>(`${API_V1}/pseudonymize/reverse`, { mapping_id: mappingId });
    return data;
  },
};

// ----- WES (GA4GH Workflow Execution Service) -----

export interface WesServiceInfo {
  id: string;
  name: string;
  type: { group: string; artifact: string; version: string };
  version: string;
  description?: string;
  system_state_counts?: Record<string, number>;
}

export interface WesRunSummary {
  run_id: string;
  state: string;
  workflow_url?: string;
  run_log?: { start_time?: string; end_time?: string };
}

export interface WesRunLogEntry {
  name?: string;
  start_time?: string;
  end_time?: string;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
}

export interface WesRunRequest {
  workflow_url: string;
  workflow_params?: Record<string, unknown>;
}

export interface WesRunLog {
  run_id: string;
  state: string;
  request?: WesRunRequest;
  run_log?: WesRunLogEntry;
  task_logs?: WesRunLogEntry[];
  outputs?: Record<string, unknown>;
}

export const wes = {
  async getServiceInfo(): Promise<WesServiceInfo> {
    const { data } = await apiClient.get<WesServiceInfo>(
      `${WES_PREFIX}/service-info`
    );
    return data;
  },
  async listRuns(params?: {
    page_size?: number;
    page_token?: string;
  }): Promise<{ runs: WesRunSummary[]; next_page_token?: string }> {
    const { data } = await apiClient.get<{
      runs: WesRunSummary[];
      next_page_token?: string;
    }>(`${WES_PREFIX}/runs`, { params });
    return data;
  },
  async submitRun(
    workflowUrl: string,
    params?: Record<string, unknown>,
    attachments?: File[]
  ): Promise<{ run_id: string }> {
    const form = new FormData();
    form.append("workflow_type", "NEXTFLOW");
    form.append("workflow_type_version", "DSL2");
    form.append("workflow_url", workflowUrl);
    if (params) {
      form.append("workflow_params", JSON.stringify(params));
    }
    if (attachments?.length) {
      for (const file of attachments) {
        form.append("workflow_attachment", file);
      }
    }
    const { data } = await apiClient.post<{ run_id: string }>(
      `${WES_PREFIX}/runs`,
      form,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );
    return data;
  },
  async cancelRun(runId: string): Promise<{ run_id: string }> {
    const { data } = await apiClient.post<{ run_id: string }>(
      `${WES_PREFIX}/runs/${encodeURIComponent(runId)}/cancel`
    );
    return data;
  },
  async getRunStatus(runId: string): Promise<{ state: string }> {
    const { data } = await apiClient.get<{ state: string }>(
      `${WES_PREFIX}/runs/${encodeURIComponent(runId)}/status`
    );
    return data;
  },
  async getRun(runId: string): Promise<WesRunLog> {
    const { data } = await apiClient.get<WesRunLog>(
      `${WES_PREFIX}/runs/${encodeURIComponent(runId)}`
    );
    return data;
  },
};

// ----- BLAST -----

export interface BlastSearchParams {
  query: string;
  database?: string;
  evalue?: number;
  max_hits?: number;
  sequence_type?: string;
  db_path?: string;
}

export const blast = {
  async getDbStatus(): Promise<{
    available: boolean;
    reason?: string;
    database?: string;
    info?: string;
    databases?: string[];
    setup?: string;
  }> {
    const { data } = await apiClient.get<{
      available: boolean;
      reason?: string;
      database?: string;
      info?: string;
      databases?: string[];
      setup?: string;
    }>(`${API_V1}/blast/db-status`);
    return data;
  },
  async search(
    query: string,
    database: string = "nt",
    params?: Omit<BlastSearchParams, "query" | "database">
  ): Promise<{ run_id: string }> {
    const { data } = await apiClient.post<{ run_id: string }>(
      `${API_V1}/blast/search`,
      { query, database, ...params }
    );
    return data;
  },
  async getResults(
    runId: string,
    options?: { papers?: boolean }
  ): Promise<{ results: BlastResult; papers?: Paper[] }> {
    const { data } = await apiClient.get<{
      results: BlastResult;
      papers?: Paper[];
    }>(`${API_V1}/blast/results/${encodeURIComponent(runId)}`, {
      params: options?.papers ? { papers: true } : undefined,
    });
    return data;
  },
};

// ----- DRS (GA4GH Data Repository Service) -----

export interface DrsObjectSummary {
  id: string;
  name?: string;
  size: number;
  created_time?: string;
  mime_type?: string;
}

export interface DrsObjectListResponse {
  objects: DrsObjectSummary[];
}

export const drs = {
  async listObjects(): Promise<DrsObjectSummary[]> {
    const { data } = await apiClient.get<DrsObjectListResponse>(
      `${DRS_PREFIX}/objects`
    );
    return data.objects ?? [];
  },
  async getObject(objectId: string): Promise<DRSObject> {
    const { data } = await apiClient.get<DRSObject>(
      `${DRS_PREFIX}/objects/${encodeURIComponent(objectId)}`
    );
    return data;
  },
  async registerObject(form: FormData): Promise<DRSObject> {
    const { data } = await apiClient.post<DRSObject>(
      `${DRS_PREFIX}/objects`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  },
  async getAccessUrl(
    objectId: string,
    accessId: string = "default"
  ): Promise<{ url: string }> {
    const { data } = await apiClient.get<{ url: string }>(
      `${DRS_PREFIX}/objects/${encodeURIComponent(objectId)}/access/${encodeURIComponent(accessId)}`
    );
    return data;
  },
  async getServiceInfo(): Promise<{
    id: string;
    name: string;
    type: { group: string; artifact: string; version: string };
    version: string;
  }> {
    const { data } = await apiClient.get(`${DRS_PREFIX}/service-info`);
    return data as {
      id: string;
      name: string;
      type: { group: string; artifact: string; version: string };
      version: string;
    };
  },
};

// ----- Phenopackets (GA4GH v2) -----

export type PhenopacketItem = Record<string, unknown>;

export interface PhenopacketCreate {
  pseudonym_id: string;
  phenotypes?: string[];
  diseases?: string[];
  genes_of_interest?: string[];
  notes?: string | null;
}

export const phenopackets = {
  async list(): Promise<PhenopacketItem[]> {
    const { data } = await apiClient.get<PhenopacketItem[]>(
      `${API_V1}/phenopackets`
    );
    return Array.isArray(data) ? data : [];
  },
  async get(id: string): Promise<PhenopacketItem> {
    const { data } = await apiClient.get<PhenopacketItem>(
      `${API_V1}/phenopackets/${encodeURIComponent(id)}`
    );
    return data;
  },
  async create(payload: PhenopacketCreate): Promise<PhenopacketItem> {
    const { data } = await apiClient.post<PhenopacketItem>(
      `${API_V1}/phenopackets`,
      payload
    );
    return data;
  },
  async delete(id: string): Promise<void> {
    await apiClient.delete(
      `${API_V1}/phenopackets/${encodeURIComponent(id)}`
    );
  },
  async export(id: string): Promise<PhenopacketItem> {
    const { data } = await apiClient.get<PhenopacketItem>(
      `${API_V1}/phenopackets/${encodeURIComponent(id)}/export`
    );
    return data;
  },
  async hpoSearch(q: string): Promise<{ id: string; name: string; definition?: string; synonyms?: string[] }[]> {
    const { data } = await apiClient.get<{ id: string; name: string; definition?: string; synonyms?: string[] }[]>(
      `${API_V1}/phenopackets/hpo/search`,
      { params: { q } }
    );
    return Array.isArray(data) ? data : [];
  },
  async extractFromText(text: string): Promise<{ terms: Array<{ hpo_id: string; name: string; confidence?: number }>; genes: string[] }> {
    const { data } = await apiClient.post<{ terms: Array<{ hpo_id: string; name: string; confidence?: number }>; genes: string[] }>(
      `${API_V1}/phenopackets/extract`,
      { text }
    );
    return data ?? { terms: [], genes: [] };
  },
};

// ----- Notebooks (Research Notebook / ELN) -----

export interface NotebookItem {
  id: string;
  title: string;
  content: string;
  tags: string[];
  linked_pmids: string[];
  linked_drs_ids: string[];
  linked_phenopacket_ids: string[];
  ai_summary: string | null;
  ai_next_steps: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NotebookListResponse {
  items: NotebookItem[];
  total: number;
  skip: number;
  limit: number;
}

export const notebooks = {
  async list(params?: {
    skip?: number;
    limit?: number;
    search?: string;
    tag?: string;
  }): Promise<NotebookListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.skip != null) searchParams.set("skip", String(params.skip));
    if (params?.limit != null) searchParams.set("limit", String(params.limit));
    if (params?.search) searchParams.set("search", params.search);
    if (params?.tag) searchParams.set("tag", params.tag);
    const qs = searchParams.toString();
    const { data } = await apiClient.get<NotebookListResponse>(
      `${API_V1}/notebooks${qs ? `?${qs}` : ""}`
    );
    return data;
  },
  async get(id: string): Promise<NotebookItem> {
    const { data } = await apiClient.get<NotebookItem>(
      `${API_V1}/notebooks/${encodeURIComponent(id)}`
    );
    return data;
  },
  async create(payload: { title?: string; content?: string; tags?: string[] }): Promise<NotebookItem> {
    const { data } = await apiClient.post<NotebookItem>(`${API_V1}/notebooks`, {
      title: payload.title ?? "",
      content: payload.content ?? "",
      tags: payload.tags ?? [],
    });
    return data;
  },
  async update(
    id: string,
    payload: { title?: string; content?: string; tags?: string[] }
  ): Promise<NotebookItem> {
    const { data } = await apiClient.put<NotebookItem>(
      `${API_V1}/notebooks/${encodeURIComponent(id)}`,
      payload
    );
    return data;
  },
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${API_V1}/notebooks/${encodeURIComponent(id)}`);
  },
  async aiAssist(id: string, mode: "summary" | "next_steps" | "both" = "both"): Promise<NotebookItem> {
    const { data } = await apiClient.post<NotebookItem>(
      `${API_V1}/notebooks/${encodeURIComponent(id)}/ai-assist`,
      { mode }
    );
    return data;
  },
  async link(id: string, type: "paper" | "drs" | "phenopacket", resourceId: string): Promise<NotebookItem> {
    const { data } = await apiClient.post<NotebookItem>(
      `${API_V1}/notebooks/${encodeURIComponent(id)}/link`,
      { type, id: resourceId }
    );
    return data;
  },
  async export(id: string, format: "md" | "pdf"): Promise<Blob> {
    const { data } = await apiClient.get<Blob>(
      `${API_V1}/notebooks/${encodeURIComponent(id)}/export`,
      { params: { format }, responseType: "blob" }
    );
    return data;
  },
};

// ----- FAIR Export -----

export interface FAIRExportOptions {
  title: string;
  description?: string;
  authors?: string[];
  license?: string;
  include_papers?: boolean;
  include_phenopackets?: boolean;
  include_notebooks?: boolean;
  include_drs?: boolean;
  keywords?: string[];
  funding?: string | null;
}

export interface FAIRComplianceReport {
  findable: boolean;
  accessible: boolean;
  interoperable: boolean;
  reusable: boolean;
  score: number;
  recommendations: string[];
}

export interface FAIRPreviewResponse {
  papers_count: number;
  phenopackets_count: number;
  notebooks_count: number;
  include_papers: boolean;
  include_phenopackets: boolean;
  include_notebooks: boolean;
  include_drs: boolean;
}

export const fairExport = {
  async preview(options: FAIRExportOptions): Promise<FAIRPreviewResponse> {
    const { data } = await apiClient.post<FAIRPreviewResponse>(
      `${API_V1}/fair-export/preview`,
      options
    );
    return data;
  },
  async complianceCheck(options: FAIRExportOptions): Promise<FAIRComplianceReport> {
    const { data } = await apiClient.post<FAIRComplianceReport>(
      `${API_V1}/fair-export/compliance-check`,
      options
    );
    return data;
  },
  async download(options: FAIRExportOptions): Promise<Blob> {
    const { data } = await apiClient.post<Blob>(
      `${API_V1}/fair-export/download`,
      options,
      { responseType: "blob" }
    );
    return data;
  },
  async zenodo(options: FAIRExportOptions, zenodoToken?: string): Promise<{
    deposition_id: string;
    doi?: string;
    record_url?: string;
    message: string;
  }> {
    const { data } = await apiClient.post<{
      deposition_id: string;
      doi?: string;
      record_url?: string;
      message: string;
    }>(`${API_V1}/fair-export/zenodo`, { options, zenodo_token: zenodoToken });
    return data;
  },
};

// ----- Health -----

export const health = {
  async check(): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get<Record<string, unknown>>(
      `${API_V1}/health`
    );
    return data;
  },
  async ready(): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get<Record<string, unknown>>(
      `${API_V1}/health/ready`
    );
    return data;
  },
};
