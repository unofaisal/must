import { Check, Flag } from "lucide-react";
import { fmtMs, groupName, sourceLabel } from "../lib/groups";
import type { Item, StageKey } from "../lib/types";

/** One stage's outcome for one email: waiting, working, skipped, or the result. */
export function StageCell({ stageKey, item }: { stageKey: StageKey; item: Item }) {
  const st = item.stages[stageKey];
  if (st.state === "waiting")
    return <span className="flex items-center gap-1.5 text-xs text-muted/70"><i className="size-2.5 rounded-full border border-line" />Waiting</span>;
  if (st.state === "running")
    return <span className="flex items-center gap-1.5 text-xs text-copper"><i className="size-3 animate-spin rounded-full border-2 border-copper border-t-transparent" />Working</span>;
  if (st.state === "skipped")
    return <span className="flex items-center gap-1.5 text-xs text-muted/70"><i className="h-px w-2.5 bg-muted/60" />Skipped</span>;

  const d = st.detail ?? {};
  let flagged = false;
  let text = "";
  if (stageKey === "safety") {
    flagged = Boolean(d.flagged);
    text = flagged ? "Flagged" : "Clear";
  } else if (stageKey === "grouping") {
    const labels = d.labels ?? [];
    text = groupName(labels[0] ?? "other") + (labels.length > 1 ? ` +${labels.length - 1}` : "");
  } else {
    text = sourceLabel(d.source);
  }
  return (
    <span className={"flex min-w-0 items-center gap-1.5 text-xs " + (flagged ? "text-bad" : "text-fg")}>
      {flagged ? <Flag className="size-3.5 shrink-0" /> : <Check className="size-3.5 shrink-0 text-good" />}
      <span className="truncate">{text}</span>
      {fmtMs(st.ms) && <span className="shrink-0 text-muted/70">{fmtMs(st.ms)}</span>}
    </span>
  );
}

/** A score from 0 to 1 with the threshold marked. `hit` means it crossed the threshold. */
export function ScoreBar({
  label, value, threshold, hit,
}: {
  label: string;
  value: number;
  threshold?: number;
  hit?: boolean;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="grid grid-cols-[1fr_5.5rem_2.5rem] items-center gap-3 py-1 text-sm">
      <span className={hit ? "text-fg" : "text-muted"}>{label}</span>
      <span
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={value}
        className="relative h-1.5 rounded-full bg-panel-2"
      >
        <span
          className={"absolute inset-y-0 left-0 rounded-full " + (hit ? "bg-copper" : "bg-muted/50")}
          style={{ width: `${pct}%` }}
        />
        {threshold != null && (
          <span
            className="absolute -top-1 h-3.5 w-px bg-fg/70"
            style={{ left: `${threshold * 100}%` }}
            title={`Threshold ${threshold}`}
          />
        )}
      </span>
      <span className="text-right text-xs tabular-nums text-muted">{value.toFixed(2)}</span>
    </div>
  );
}
