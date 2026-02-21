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

export const literature = {
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
