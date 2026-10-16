import { useMemo, useState, type ReactNode } from "react";
import { Check } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { SAFETY_QUESTIONS, STAGES, fmtElapsed, groupName, isOpen, sourceLabel } from "../lib/groups";
import { useStore } from "../lib/store";
import type { Item } from "../lib/types";
import { ScoreBar, StageCell } from "./parts";

const FEED_COLS = "grid-cols-[2.25rem_minmax(0,1.4fr)_repeat(3,minmax(0,1fr))]";

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="border-t border-line pt-4">
      <h3 className="flex items-center gap-2 text-sm font-medium">
        <span className="grid size-5 place-items-center rounded-full bg-panel-2 text-xs text-copper">{n}</span>
        {title}
      </h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function Inspector({ item, runDone, onReview }: { item: Item; runDone: boolean; onReview: (key: string) => void }) {
  const [showAll, setShowAll] = useState(false);
  const { safety, grouping, drafting } = item.stages;
  const sd = safety.detail ?? {};
  const gd = grouping.detail ?? {};
  const scores = Object.entries(gd.scores ?? {}).filter(([k]) => k !== "other").sort((a, b) => b[1] - a[1]);
  const shown = showAll ? scores : scores.slice(0, 5);
  const labels = gd.labels ?? [];
  const muted = "text-sm text-muted";

  return (
    <aside aria-label={`Pipeline detail for ${item.sender}`} className="flex max-h-[85dvh] flex-col gap-4 overflow-y-auto overscroll-contain rounded-lg border border-line bg-panel p-5 xl:sticky xl:top-2 xl:max-h-[calc(100dvh-1.5rem)]">
      <div>
        <h2 className="font-display text-2xl">{item.sender}</h2>
        <p className="mt-1 text-sm font-medium">{item.subject}</p>
        <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap text-muted">{item.body}</p>
      </div>

      <Step n={1} title="Safety check">
        {safety.state === "done" ? (
          <>
            {Object.entries(SAFETY_QUESTIONS).map(([q, label]) =>
              sd.flags?.[q] != null ? (
                <ScoreBar key={q} label={label} value={sd.flags[q]} threshold={sd.threshold} hit={sd.flags[q] >= (sd.threshold ?? 1)} />
              ) : null,
            )}
            {sd.flagged ? (
              <>
                <p className="mt-2 text-sm text-bad">{sd.error ? "Something broke here, so a human reads it." : "Stopped here. No draft was written."}</p>
                <ul className="mt-1 list-disc pl-5 text-sm text-bad">{(sd.reasons ?? []).map((r) => <li key={r}>{r}</li>)}</ul>
              </>
            ) : (
              <p className="mt-2 text-sm text-good">Clear. Every score is under {sd.threshold}.</p>
            )}
          </>
        ) : (
          <p className={muted}>{safety.state === "running" ? "Checking now." : "Waiting for its turn."}</p>
        )}
      </Step>

      <Step n={2} title="Grouping">
        {grouping.state === "done" ? (
          <>
            {shown.map(([k, v]) => <ScoreBar key={k} label={groupName(k)} value={v} threshold={gd.threshold} hit={labels.includes(k)} />)}
            {scores.length > 5 && (
              <button type="button" className="mt-1 text-xs text-copper underline" onClick={() => setShowAll(!showAll)}>
                {showAll ? "Show fewer" : `Show all ${scores.length}`}
              </button>
            )}
            <p className="mt-2 text-sm">
              {labels[0] === "other"
                ? `No group scored ${gd.threshold} or higher, so it goes to Something else.`
                : `Grouped as ${groupName(labels[0] ?? "other")}${labels.length > 1 ? `, also ${labels.slice(1).map(groupName).join(", ")}` : ""}.`}
            </p>
          </>
        ) : (
          <p className={muted}>
            {grouping.state === "skipped" ? "Skipped, because the safety check flagged it." : grouping.state === "running" ? "Scoring now." : "Waiting for the safety check."}
          </p>
        )}
      </Step>

      <Step n={3} title="Drafting">
        {drafting.state === "done" ? (
          <>
            <blockquote className="border-l-2 border-copper pl-3 font-display text-base leading-relaxed whitespace-pre-wrap">{item.draft}</blockquote>
            <p className={muted + " mt-2"}>{sourceLabel(drafting.detail?.source)}.</p>
          </>
        ) : (
          <p className={muted}>
            {drafting.state === "skipped" ? "No draft. A human writes this reply." : drafting.state === "running" ? "Writing now." : "Waiting for grouping."}
          </p>
        )}
      </Step>

      {runDone && (
        <button type="button" onClick={() => onReview(item.key)} className="self-start rounded-full bg-copper px-5 py-2 text-sm font-medium text-copper-deep">
          Open in review
        </button>
      )}
    </aside>
  );
}

type StationState = "done" | "active" | "waiting";

export function Pipeline() {
  const { batch, selected, select } = useStore();
  const navigate = useNavigate();
  const { items, run } = batch;
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const total = items.length;
  const running = run.state === "running";

  const s = useMemo(() => {
    const per = {} as Record<string, { passed: number; running: number }>;
    for (const st of STAGES) {
      const states = items.map((i) => i.stages[st.key].state);
      per[st.key] = {
        passed: states.filter((x) => x === "done" || x === "skipped").length,
        running: states.filter((x) => x === "running").length,
      };
    }
    const flagged = items.filter((i) => i.stages.safety.detail?.flagged).length;
    const safetyDone = items.filter((i) => i.stages.safety.state === "done").length;
    const drafted = items.filter((i) => i.stages.drafting.state === "done");
    const src = (i: Item) => i.stages.drafting.detail?.source ?? "";
    return {
      per, flagged, clear: safetyDone - flagged,
      groupsUsed: new Set(items.filter((i) => i.stages.grouping.state === "done").flatMap((i) => i.labels)).size,
      model: drafted.filter((i) => !src(i).startsWith("template")).length,
      template: drafted.filter((i) => src(i) === "template").length,
      fellBack: drafted.filter((i) => src(i) === "template (fallback)").length,
      ready: items.filter((i) => i.processing === "done").length,
      handled: items.filter((i) => i.processing === "done" && i.status !== "pending").length,
    };
  }, [items]);

  const stateOf = (passed: number, runningN: number, all: number): StationState =>
    all > 0 && passed === all ? "done" : runningN > 0 || passed > 0 ? "active" : "waiting";

  const stations: { key: string; label: string; passed: number; of: number; state: StationState; summary: ReactNode }[] = [
    { key: "safety", label: "Safety check", passed: s.per.safety.passed, of: total,
      state: stateOf(s.per.safety.passed, s.per.safety.running, total),
      summary: <>{s.clear} clear, <b>{s.flagged} flagged</b></> },
    { key: "grouping", label: "Grouping", passed: s.per.grouping.passed, of: total,
      state: stateOf(s.per.grouping.passed, s.per.grouping.running, total),
      summary: <>{s.groupsUsed} {s.groupsUsed === 1 ? "group" : "groups"} in use</> },
    { key: "drafting", label: "Drafting", passed: s.per.drafting.passed, of: total,
      state: stateOf(s.per.drafting.passed, s.per.drafting.running, total),
      summary: <>{s.model} by model, {s.template} template{s.fellBack ? `, ${s.fellBack} fell back` : ""}</> },
    { key: "review", label: "Your review", passed: s.handled, of: s.ready,
      state: !running && s.ready > 0 && s.handled === s.ready ? "done" : s.handled > 0 || (!running && s.ready > 0) ? "active" : "waiting",
      summary: running ? "Opens when the run finishes" : `${s.ready - s.handled} still to review` },
  ];

  const rows = onlyFlagged ? items.filter((i) => i.stages.safety.detail?.flagged) : items;
  const current = items.find((i) => i.key === selected);

  function openReview(key?: string) {
    const first = items.find(isOpen) ?? items[0];
    select(key ?? first?.key ?? null);
    void navigate({ to: "/review" });
  }

  return (
    <main className="h-full overflow-auto px-6 py-8 sm:px-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl tracking-tight">
            {running ? `Processing ${run.done} of ${run.total} emails` : `${total} emails processed in ${fmtElapsed(run.elapsed)}`}
          </h1>
          <p className="mt-2 text-sm text-muted">
            {running
              ? `Working for ${fmtElapsed(run.elapsed)}. Click any email to see what each step decided.`
              : `${s.flagged} flagged for a human, ${total - s.flagged} drafted. Nothing has been sent.`}
          </p>
        </div>
        {!running && (
          <button type="button" onClick={() => openReview()} className="rounded-full bg-copper px-6 py-3 text-sm font-medium text-copper-deep">
            Start reviewing
          </button>
        )}
      </header>

      <ol aria-label="Pipeline progress" className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {stations.map((st, idx) => (
          <li key={st.key} data-state={st.state}
            className={"rounded-lg border p-4 " + (st.state === "active" ? "border-copper bg-panel" : "border-line bg-panel/60")}>
            <div className="flex items-center gap-2">
              <span className={"grid size-6 place-items-center rounded-full text-xs " + (st.state === "done" ? "bg-good text-ink" : "bg-panel-2 text-muted")}>
                {st.state === "done" ? <Check className="size-3.5" /> : idx + 1}
              </span>
              <h2 className="text-sm font-medium">{st.label}</h2>
            </div>
            <p className="mt-3 text-sm text-muted"><strong className="font-display text-2xl text-fg">{st.passed}</strong> of {st.of}</p>
            <span className="mt-2 block h-1 overflow-hidden rounded-full bg-panel-2">
              <span className="block h-full bg-copper transition-[width] duration-300" style={{ width: `${st.of ? (st.passed / st.of) * 100 : 0}%` }} />
            </span>
            <p className="mt-2 text-xs text-muted">{st.summary}</p>
          </li>
        ))}
      </ol>

      <div className="mt-8 grid items-start gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <section className="min-w-0">
          <div className="flex items-center justify-between pb-2 text-sm text-muted">
            <span>{rows.length} {rows.length === 1 ? "email" : "emails"}</span>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={onlyFlagged} onChange={(e) => setOnlyFlagged(e.target.checked)} className="accent-[var(--color-copper)]" />
              Only flagged ({s.flagged})
            </label>
          </div>
          <div className="overflow-x-auto rounded-lg border border-line">
            <div className="min-w-[34rem]">
              <div aria-hidden="true" className={`grid ${FEED_COLS} gap-3 border-b border-line bg-panel px-3 py-2 text-[11px] tracking-widest text-muted uppercase`}>
                <span>#</span><span>Email</span>
                {STAGES.map((st) => <span key={st.key}>{st.label}</span>)}
              </div>
              <ul>
                {rows.map((i) => (
                  <li key={i.key}>
                    <button type="button" aria-pressed={i.key === selected} onClick={() => select(i.key)}
                      className={`grid w-full ${FEED_COLS} items-center gap-3 border-b border-line px-3 py-2.5 text-left last:border-b-0 ` + (i.key === selected ? "bg-panel-2" : "hover:bg-panel")}>
                      <span className="truncate text-xs text-muted tabular-nums" title={`Message id: ${i.id}`}>{items.indexOf(i) + 1}</span>
                      <span className="flex min-w-0 flex-col">
                        <strong className="truncate text-sm font-medium">{i.sender}</strong>
                        <span className="truncate text-xs text-muted">{i.subject}</span>
                      </span>
                      {STAGES.map((st) => <StageCell key={st.key} stageKey={st.key} item={i} />)}
                    </button>
                  </li>
                ))}
                {rows.length === 0 && <li className="px-3 py-8 text-sm text-muted">No emails were flagged.</li>}
              </ul>
            </div>
          </div>
        </section>

        {current ? (
          <Inspector key={current.key} item={current} runDone={!running} onReview={openReview} />
        ) : (
          <aside className="rounded-lg border border-dashed border-line p-6 text-sm text-muted">
            Select an email to see what each step decided about it.
          </aside>
        )}
      </div>
    </main>
  );
}