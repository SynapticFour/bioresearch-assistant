/**
 * Shared TypeScript interfaces for BioResearch Assistant frontend.
 * Aligned with backend Pydantic schemas where applicable.
 */

export interface Paper {
  pmid: string;
  title: string;
  abstract: string;
  authors: string[];
  year: string | null;
  journal: string;
  summary?: string;
  /** Key findings (when from enriched API). */
  key_findings?: string[];
  /** Methods (when from enriched API). */
  methods?: string[];
  /** Keywords / MeSH (when from enriched API). */
  keywords?: string[];
}

export interface EntityFound {
  type: string;
  start: number;
  end: number;
}

export interface PseudonymizeResult {
  pseudonymized_text: string;
  entities_found: EntityFound[];
  mapping_id: string | null;
}

export interface WorkflowRun {
  run_id: string;
  state: string;
  workflow_url?: string;
  start_time?: string;
  end_time?: string;
}

export interface BlastHit {
  hit_id: string;
  hit_def?: string;
  hit_len?: number;
  hsps: Array<{
    score: number;
    expect?: number;
    identities?: number;
    align_length?: number;
    query_start?: number;
    query_end?: number;
    hit_start?: number;
    hit_end?: number;
    query?: string;
    match?: string;
    hit?: string;
  }>;
}

export interface BlastStatistics {
  database?: string;
  program?: string;
  version?: string;
  num_sequences?: number;
  num_hits: number;
  top_hit_ids: string[];
}

export interface BlastResult {
  run_id: string;
  hits: BlastHit[];
  statistics: BlastStatistics;
  raw_outputs?: Record<string, unknown>;
}

export interface DrsChecksum {
  checksum: string;
  type: string;
}

export interface DrsAccessUrl {
  url: string;
  headers?: string[];
}

export interface DrsAccessMethod {
  type: string;
  access_url?: DrsAccessUrl;
  access_id?: string;
}

export interface DRSObject {
  id: string;
  name?: string;
  size: number;
  checksums: DrsChecksum[];
  access_methods?: DrsAccessMethod[];
  self_uri?: string;
  created_time?: string;
  updated_time?: string;
  version?: string;
  mime_type?: string;
  description?: string;
}

export interface AuditLogEntry {
  operation_id: string;
  timestamp: string;
  entities_count: number;
  operation_type: string;
  user_id?: string | null;
  input_hash?: string;
}
