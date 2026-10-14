// Display order and plain-language names for the groups the pipeline produces.
export const GROUPS = [
  { key: "quarantined", label: "Needs a human first", hint: "The safety check stopped these. No draft was written." },
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
  { key: "other", label: "Something else", hint: "Nothing matched clearly. Read these closely." },
];

const NAMES = Object.fromEntries(GROUPS.map((g) => [g.key, g.label]));
export const groupName = (key) => NAMES[key] || key;
export const groupOf = (item) => (item.kind === "quarantined" ? "quarantined" : item.primary);
