import { useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Trash2 } from "lucide-react";
import { useActions } from "@/lib/actions";
import { fmtDate } from "@/lib/groups";
import { useStore } from "@/lib/store";
import type { HistoryEntry } from "@/lib/types";

function Chip({ n, label, tone }: { n: number; label: string; tone?: "copper" | "good" }) {
  if (!n) return null;
  const cls = tone === "copper" ? "bg-copper/15 text-copper" : tone === "good" ? "bg-good/20 text-good" : "bg-panel-2 text-muted";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs ${cls}`}>{n} {label}</span>;
}

export function BatchRow({ entry }: { entry: HistoryEntry }) {
  const { openPast } = useActions();
  const { removeBatch, running } = useStore();
  const c = entry.counts;

  function remove() {
    if (window.confirm(`Delete "${entry.name}"? Its drafts and decisions are removed. Approved replies you have not exported will be lost.`))
      void removeBatch(entry.id);
  }

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border border-line bg-panel px-4 py-3.5">
      <div className="min-w-0 flex-1 basis-56">
        <p className="flex items-center gap-2">
          <span className="truncate font-medium">{entry.name}</span>
          {entry.open && <span className="rounded-full bg-copper px-2 py-0.5 text-[10px] font-medium tracking-wide text-copper-deep uppercase">Open now</span>}
        </p>
        <p className="mt-0.5 text-xs text-muted">{fmtDate(entry.created)} · {entry.total} emails</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Chip n={c.pending} label="to review" tone="copper" />
          <Chip n={c.approved} label="approved" tone="good" />
          <Chip n={c.sent} label="sent" tone="good" />
          <Chip n={c.rejected} label="rejected" />
          <Chip n={entry.quarantined} label="held for a human" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => void openPast(entry.id)} disabled={running && !entry.open}
          title={running && !entry.open ? "Available when the current run finishes" : undefined}
          className="inline-flex items-center gap-2 rounded-full bg-fg px-4 py-2 text-sm font-medium text-ink disabled:opacity-40">
          {entry.open ? "Continue" : "Open"}<ArrowRight className="size-4" />
        </button>
        <button type="button" aria-label={`Delete ${entry.name}`} onClick={remove} disabled={running && entry.open}
          className="rounded-full p-2 text-muted hover:bg-panel-2 hover:text-bad disabled:opacity-40">
          <Trash2 className="size-4" />
        </button>
      </div>
    </li>
  );
}

export function History() {
  const { history, refreshHistory } = useStore();
  useEffect(() => { void refreshHistory(); }, [refreshHistory]);

  return (
    <main className="h-full overflow-auto px-6 py-8 sm:px-10">
      <h1 className="font-display text-4xl tracking-tight">Past work</h1>
      <p className="mt-2 max-w-xl text-sm text-muted">
        Every finished batch is kept on this machine, with your edits and decisions. Open one to pick up where you stopped.
        The newest 50 are kept.
      </p>
      {history.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-line p-8 text-center">
          <p className="font-display text-2xl">Nothing here yet.</p>
          <p className="mt-2 text-sm text-muted">Batches appear here once their run finishes.</p>
          <Link to="/" className="mt-4 inline-block rounded-full bg-copper px-5 py-2 text-sm font-medium text-copper-deep">Start a batch</Link>
        </div>
      ) : (
        <ul className="mt-8 flex max-w-3xl flex-col gap-3">
          {history.map((e) => <BatchRow key={e.id} entry={e} />)}
        </ul>
      )}
    </main>
  );
}
