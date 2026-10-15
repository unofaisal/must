import type { Item, StageKey } from "./types";

// Plain-language names, in display order, for everything the pipeline produces.
export const GROUPS = [
  { key: "quarantined", label: "Needs a human first" },
  { key: "status_update", label: "Status updates" },
  { key: "reschedule", label: "Scheduling" },
  { key: "hiring_process", label: "Hiring process" },
  { key: "pay_or_contract", label: "Pay and contract" },
  { key: "technical_issue", label: "Technical issues" },
  { key: "deadline_extension", label: "Deadline extensions" },
  { key: "submission_or_documents", label: "Documents and submissions" },
  { key: "feedback", label: "Feedback" },
  { key: "withdrawal", label: "Withdrawals" },
  { key: "thanks_or_ack", label: "Thanks" },
  { key: "other", label: "Something else" },
] as const;

const NAMES: Record<string, string> = Object.fromEntries(GROUPS.map((g) => [g.key, g.label]));
export const groupName = (key: string): string => NAMES[key] ?? key;
export const groupOf = (item: Item): string => (item.kind === "quarantined" ? "quarantined" : item.primary);

export const SAFETY_QUESTIONS: Record<string, string> = {
  gives_instructions: "Gives the assistant instructions, or claims to be staff",
  asks_about_other: "Asks about another candidate or internal information",
  angry_or_distressed: "Angry, threatening, or distressed",
};

export const STAGES: { key: StageKey; label: string }[] = [
  { key: "safety", label: "Safety check" },
  { key: "grouping", label: "Grouping" },
  { key: "drafting", label: "Drafting" },
];

export const sourceLabel = (source?: string): string =>
  source === "template" ? "Template" : source === "template (fallback)" ? "Template, model failed" : "Model draft";

export function fmtElapsed(sec: number): string {
  if (sec < 60) return `${sec.toFixed(1)} s`;
  return `${Math.floor(sec / 60)} min ${Math.round(sec % 60)} s`;
}

export function fmtMs(ms: number | null | undefined): string {
  if (ms == null || ms < 100) return "";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

export const PLACEHOLDER = /\[([^[\]]+)\]/g;
export const missingPlaceholders = (text: string): string[] =>
  [...text.matchAll(PLACEHOLDER)].map((m) => m[1]);

export const isOpen = (i: Item): boolean => i.status === "pending" || i.status === "approved";

export function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}
