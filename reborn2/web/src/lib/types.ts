// Shapes returned by the FastAPI backend (api/service.py).

export type Status = "pending" | "approved" | "rejected" | "sent";
export type StageKey = "safety" | "grouping" | "drafting";
export type StageState = "waiting" | "running" | "done" | "skipped";

export interface StageDetail {
  flagged?: boolean;
  error?: boolean | string;
  flags?: Record<string, number>;
  threshold?: number;
  reasons?: string[];
  scores?: Record<string, number>;
  labels?: string[];
  source?: string;
}

export interface Stage {
  state: StageState;
  detail: StageDetail;
  ms: number | null;
}

export interface Item {
  key: string;
  id: string;
  sender: string;
  email: string;
  subject: string;
  body: string;
  /** "gmail" when the message was pulled from Gmail; replies then go out through Gmail. */
  source?: "csv" | "gmail";
  status: Status;
  sent_at: string | null;
  kind: "draft" | "quarantined";
  labels: string[];
  primary: string;
  confidence: string;
  draft: string;
  draft_source: string;
  reasons: string[];
  processing: "queued" | "running" | "done";
  stages: Record<StageKey, Stage>;
  placeholders: string[];
}

export interface ProviderErrors {
  chat?: { errors: number; last: string };
  decide?: { errors: number; last: string };
}

export interface RunInfo {
  state: "idle" | "running" | "done";
  total: number;
  done: number;
  elapsed: number;
  demo_delay_ms: number;
  provider_errors: ProviderErrors;
}

export interface BatchMeta {
  id: string;
  name: string;
  created: string;
}

export interface HistoryEntry {
  id: string;
  name: string;
  created: string;
  saved_at: string;
  total: number;
  quarantined: number;
  counts: { pending: number; approved: number; rejected: number; sent: number };
  open: boolean;
}

export interface Batch {
  mode: "live" | "offline";
  batch?: BatchMeta | null;
  run: RunInfo;
  items: Item[];
}

export interface Settings {
  api_key_set: boolean;
  api_key_hint: string;
  chat_model: string;
  decide_model: string;
  custom_prompt: string;
  mode: "live" | "offline";
}

export interface SettingsPatch {
  api_key?: string;
  chat_model?: string;
  decide_model?: string;
  custom_prompt?: string;
}

export interface GmailStatus {
  client_id: string;
  secret_set: boolean;
  secret_hint: string;
  mcp_url: string;
  scopes: string;
  redirect_uri: string;
  configured: boolean;
  connected: boolean;
  connected_at: string;
}

export interface GmailConfigPatch {
  client_id?: string;
  client_secret?: string;
  mcp_url?: string;
  scopes?: string;
  redirect_uri?: string;
}

export interface GmailTest {
  ok: boolean;
  tools: string[];
  missing: string[];
}

export interface GmailFetchParams {
  keywords: string;
  after: string;
  before: string;
  limit: number;
}

export interface CheckResult {
  key_present: boolean;
  key_hint: string;
  models: { chat: string; decide: string } | null;
  chat: { ok: boolean; ms?: number; error?: string } | null;
  decide: { ok: boolean; ms?: number; error?: string } | null;
}
