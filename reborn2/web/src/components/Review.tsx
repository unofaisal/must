import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { Check, Mail, Send } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { patchItem, sendItem } from "../lib/api";
import { GROUPS, groupName, groupOf, isOpen, missingPlaceholders, sourceLabel } from "../lib/groups";
import { MAILTO_SAFE_LENGTH, mailtoUrl } from "../lib/mail";
import { useStore } from "../lib/store";
import type { Item, Status } from "../lib/types";

type TabKey = "open" | "sent" | "rejected" | "all";
const TABS: { key: TabKey; label: string; match: (i: Item) => boolean }[] = [
  { key: "open", label: "Open", match: isOpen },
  { key: "sent", label: "Sent", match: (i) => i.status === "sent" },
  { key: "rejected", label: "Rejected", match: (i) => i.status === "rejected" },
  { key: "all", label: "All", match: () => true },
];

interface Actions {
  approve: () => void;
  reject: () => void;
  send: () => void;
}

function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setMatches(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return matches;
}

const STATUS_LABEL: Record<Status, string> = {
  pending: "To review",
  approved: "Approved",
  sent: "Sent",
  rejected: "Rejected",
};

function Letter({ item, actionsRef }: { item: Item; actionsRef: MutableRefObject<Actions | null> }) {
  const { replaceItem, select } = useStore();
  const navigate = useNavigate();
  const [text, setText] = useState(item.draft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [opened, setOpened] = useState(false); // the mail app has been opened for this reply
  const [mailNote, setMailNote] = useState("");
  const latest = useRef(0); // only the newest request may update the pane

  useEffect(() => setText(item.draft), [item.draft]);
  useEffect(() => {
    setOpened(false);
    setMailNote("");
  }, [item.status]);

  const locked = item.status === "sent";
  const quarantined = item.kind === "quarantined";
  const missing = missingPlaceholders(text);
  const canApprove = text.trim() !== "" && missing.length === 0;
  const { grouping, drafting, safety } = item.stages;

  async function call(request: () => Promise<Item>, blocking = true) {
    const id = ++latest.current;
    if (blocking) setBusy(true);
    setError("");
    try {
      const updated = await request();
      if (id === latest.current) replaceItem(updated);
    } catch (e) {
      if (id === latest.current) setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      if (blocking && id === latest.current) setBusy(false);
    }
  }

  // Saving on blur must never disable the buttons, or a click on Approve gets lost.
  const saveDraft = () => {
    if (!locked && text !== item.draft) void call(() => patchItem(item.key, { draft: text }), false);
  };
  const approve = () => call(() => patchItem(item.key, { draft: text, status: "approved" }));
  const reject = () => call(() => patchItem(item.key, { status: "rejected" }));
  const reopen = () => call(() => patchItem(item.key, { status: "pending" }));
  const markSent = () => call(() => sendItem(item.key));
  const viaGmail = item.source === "gmail";
  // A real email goes out, so ask once. The person already approved the text.
  const sendViaGmail = async () => {
    if (!window.confirm(`Send this reply to ${item.email || "the sender"} through Gmail? It can't be undone.`)) return;
    await call(() => sendItem(item.key));
  };

  // Opens the default mail app with the recipient, subject and approved reply filled in.
  // A web page cannot tell whether the message was actually sent, so the person confirms
  // that with "Mark as sent" afterwards.
  function openMail() {
    const url = mailtoUrl(item, item.draft);
    if (url.length > MAILTO_SAFE_LENGTH) {
      void navigator.clipboard?.writeText(item.draft).catch(() => {});
      setMailNote("This reply is long, so it is also copied to your clipboard in case your mail app cuts it off.");
    } else if (!item.email.trim()) {
      setMailNote("This candidate has no email address. Add the recipient in your mail app.");
    } else {
      setMailNote("");
    }
    setOpened(true);
    window.location.href = url;
  }

  // The keyboard shortcuts in <Review> call these.
  actionsRef.current = {
    approve: () => { if (item.status === "pending" && canApprove && !busy) void approve(); },
    reject: () => { if (item.status === "pending" && !busy) void reject(); },
    send: () => { if (item.status === "approved" && !busy) { if (viaGmail) void sendViaGmail(); else openMail(); } },
  };

  const topScore = grouping.detail?.scores?.[item.primary];
  const hint = text.trim() === "" ? "Write a reply to approve." : missing.length ? `Fill in ${missing.map((m) => `[${m}]`).join(", ")} before approving.` : "";
  const pill = "rounded-full border border-cream-2 px-4 py-2 text-sm disabled:opacity-40";
  const solid = "inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2 text-sm text-fg disabled:opacity-40";

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8 sm:px-10">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs tracking-[0.18em] text-copper-deep uppercase">
            {quarantined ? "Needs a human first" : groupName(item.primary)}
            {!quarantined && item.labels.length > 1 && ` + ${item.labels.slice(1).map(groupName).join(", ")}`}
          </p>
          <h2 className="mt-1 font-display text-4xl tracking-tight">{item.sender || "Unknown sender"}</h2>
          {item.email && <p className="mt-1 text-sm text-copper-deep/80">{item.email}</p>}
        </div>
        <span className="shrink-0 rounded-full bg-cream-2 px-3 py-1 text-xs font-medium tracking-wide uppercase">
          {STATUS_LABEL[item.status]}
        </span>
      </div>

      <article className="mt-8 rounded-lg bg-sheet px-6 py-5 shadow-sm">
        <h3 className="text-xs tracking-widest text-copper-deep uppercase">They wrote</h3>
        <p className="mt-2 font-medium">{item.subject || "(no subject)"}</p>
        <p className="mt-3 font-display text-lg leading-relaxed whitespace-pre-wrap">{item.body}</p>
      </article>

      {quarantined && (
        <ul className="mt-4 list-disc pl-5 text-sm text-bad">
          {item.reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
      )}

      <label className="mt-6 block flex-1">
        <span className="text-xs tracking-widest text-copper-deep uppercase">Your reply</span>
        <textarea
          value={text}
          readOnly={locked}
          onChange={(e) => setText(e.target.value)}
          onBlur={saveDraft}
          placeholder={quarantined ? "No draft was written. Write your own reply, or reject to dismiss." : ""}
          className="mt-2 min-h-40 w-full resize-y rounded-lg border border-cream-2 bg-sheet px-5 py-4 font-display text-lg leading-relaxed outline-none focus:border-copper"
        />
      </label>
      {missing.length > 0 && item.status === "pending" && (
        <p className="mt-2 text-sm text-bad">Fill in {missing.map((m) => `[${m}]`).join(", ")} before approving.</p>
      )}

      <div className="mt-4 rounded-lg border border-cream-2 px-4 py-3 text-sm text-copper-deep">
        <p className="text-xs tracking-widest uppercase">How it got here</p>
        <p className="mt-1.5">
          Safety: {safety.detail?.flagged ? "flagged, stopped before grouping" : "clear"}
          <span className="mx-2 opacity-40">·</span>
          Grouping: {grouping.state === "skipped" ? "skipped" : `${groupName(item.primary)}${topScore != null ? `, score ${topScore.toFixed(2)}` : ""}`}
          <span className="mx-2 opacity-40">·</span>
          Draft: {drafting.state === "skipped" ? "none, you write it" : sourceLabel(item.draft_source)}
        </p>
        <button type="button" className="mt-1.5 underline" onClick={() => { select(item.key); void navigate({ to: "/pipeline" }); }}>
          See the scores
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {item.status === "pending" && (
          <>
            <button type="button" className={pill} disabled={busy} title="Shortcut: X" onClick={reject}>Reject</button>
            <button type="button" className={solid} disabled={busy || !canApprove} title={hint || "Shortcut: A"} onClick={approve}>Approve</button>
          </>
        )}
        {item.status === "approved" && (
          <>
            <button type="button" className={pill} disabled={busy} onClick={reopen}>Undo approval</button>
            {viaGmail ? (
              <button type="button" className={solid} disabled={busy} title="Shortcut: S" onClick={sendViaGmail}>
                <Send className="size-4" />{busy ? "Sending…" : "Send via Gmail"}
              </button>
            ) : (
              <>
                <button type="button" className={opened ? pill : solid} disabled={busy} title="Shortcut: S" onClick={openMail}>
                  <Mail className="size-4" />{opened ? "Open mail app again" : "Open in mail app"}
                </button>
                <button type="button" className={opened ? solid : pill} disabled={busy} onClick={markSent}
                  title="Click once you have sent it from your mail app">
                  <Check className="size-4" />Mark as sent
                </button>
              </>
            )}
          </>
        )}
        {item.status === "rejected" && <button type="button" className={pill} disabled={busy} onClick={reopen}>Restore</button>}
        {item.status === "sent" && (
          <p className="text-sm text-copper-deep">
            {viaGmail ? "Sent through Gmail" : "Marked as sent"} {item.sent_at ? new Date(item.sent_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : ""}. Recorded in outbox/sent.csv.
          </p>
        )}
        {error && (
          <p role="alert" className="flex w-full items-start gap-3 text-sm text-bad">
            <span>{error}</span>
            <button type="button" className="ml-auto shrink-0 underline" onClick={() => setError("")}>Dismiss</button>
          </p>
        )}
        {item.status === "approved" && (
          <p className="w-full text-xs text-copper-deep">
            {viaGmail
              ? "Sends this as a reply inside the original Gmail thread."
              : mailNote || (opened ? "Send it from your mail app, then mark it as sent here." : "Opens your mail app with the recipient, subject and reply filled in.")}
          </p>
        )}
        <p className="ml-auto hidden text-xs text-copper-deep/70 sm:block">J / K move · A approve · S {viaGmail ? "send" : "open mail"} · X reject</p>
      </div>
    </div>
  );
}

export function Review() {
  const { batch, selected, select } = useStore();
  const items = batch.items;
  const desktop = useMedia("(min-width: 768px)");
  const [tab, setTab] = useState<TabKey>("open");
  const [sheet, setSheet] = useState(false);
  const actionsRef = useRef<Actions | null>(null);
  const lastIndex = useRef(0);

  const tabMatch = TABS.find((t) => t.key === tab)!.match;
  const sections = useMemo(
    () => GROUPS.map((g) => ({ ...g, rows: items.filter((i) => groupOf(i) === g.key && tabMatch(i)) })).filter((s) => s.rows.length),
    [items, tabMatch],
  );
  const flat = useMemo(() => sections.flatMap((s) => s.rows), [sections]);
  const counts = Object.fromEntries(TABS.map((t) => [t.key, items.filter(t.match).length]));
  const handled = items.filter((i) => i.status !== "pending").length;
  const current = flat.find((i) => i.key === selected) ?? null;

  // Keep a message selected. When the current one leaves the list (sent, rejected),
  // move to whatever now sits in its place.
  useEffect(() => {
    if (!flat.length) return;
    const idx = flat.findIndex((i) => i.key === selected);
    if (idx === -1) select(flat[Math.min(lastIndex.current, flat.length - 1)].key);
    else lastIndex.current = idx;
  }, [flat, selected, select]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") return;
      const idx = flat.findIndex((i) => i.key === selected);
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        if (flat[idx + 1]) select(flat[idx + 1].key);
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        if (flat[idx - 1]) select(flat[idx - 1].key);
      } else if (e.key === "a") actionsRef.current?.approve();
      else if (e.key === "s") actionsRef.current?.send();
      else if (e.key === "x") actionsRef.current?.reject();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flat, selected, select]);

  const empty = (
    <div className="grid h-full place-items-center px-8 text-center">
      <div>
        <h2 className="font-display text-3xl">{tab === "open" ? "All caught up." : "Nothing to show."}</h2>
        <p className="mt-2 text-sm text-copper-deep">
          {tab === "open" ? "Every reply is approved, sent, or rejected. Export the approved ones from the sidebar." : "Pick another tab to see more."}
        </p>
      </div>
    </div>
  );

  return (
    <div className="flex h-full min-h-0">
      <section className="flex min-h-0 min-w-0 flex-1 flex-col border-r border-line bg-ink md:w-[22rem] md:flex-none">
        <div className="flex gap-1 border-b border-line px-3 py-2">
          {TABS.map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}
              className={"rounded-full px-3 py-1.5 text-xs font-medium " + (tab === t.key ? "bg-fg text-ink" : "text-muted hover:text-fg")}>
              {t.label} <span className="opacity-60">{counts[t.key]}</span>
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          {sections.map((s) => (
            <section key={s.key}>
              <h2 className={"sticky top-0 z-[1] flex items-center justify-between border-b border-line bg-panel px-4 py-1.5 text-[11px] tracking-widest uppercase " + (s.key === "quarantined" ? "text-bad" : "text-muted")}>
                {s.label}<span>{s.rows.length}</span>
              </h2>
              <ul>
                {s.rows.map((m) => (
                  <li key={m.key}>
                    <button type="button" aria-current={m.key === selected}
                      onClick={() => { select(m.key); setSheet(true); }}
                      className={"flex w-full flex-col gap-0.5 border-b border-line px-4 py-3 text-left " + (m.key === selected ? "bg-panel-2" : "hover:bg-panel")}>
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium">{m.sender}</span>
                        {m.status === "approved" && <Check className="size-3.5 shrink-0 text-good" aria-label="Approved" />}
                      </span>
                      <span className="truncate text-xs text-muted">{m.subject}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {!flat.length && <p className="px-4 py-10 text-sm text-muted">{tab === "open" ? "Nothing left to review." : "Nothing here yet."}</p>}
        </div>
        <div className="border-t border-line px-4 py-3 text-xs text-muted">
          <strong className="text-fg">{handled}</strong> of {items.length} handled
        </div>
      </section>

      {desktop ? (
        <section className="min-w-0 flex-1 overflow-auto bg-cream text-ink">
          {current ? <Letter key={current.key} item={current} actionsRef={actionsRef} /> : empty}
        </section>
      ) : (
        sheet && current && (
          <div className="fixed inset-0 z-20 flex flex-col bg-cream text-ink">
            <button type="button" className="px-4 py-3 text-left text-sm" onClick={() => setSheet(false)}>Back to list</button>
            <div className="min-h-0 flex-1 overflow-auto">
              <Letter key={current.key} item={current} actionsRef={actionsRef} />
            </div>
          </div>
        )
      )}
    </div>
  );
}
