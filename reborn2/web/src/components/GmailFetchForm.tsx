import { useEffect, useState } from "react";
import { Mail, X } from "lucide-react";
import { getGmail } from "../lib/api";
import type { GmailFetchParams, GmailStatus } from "../lib/types";

const fieldCls = "w-full rounded-md border border-line bg-ink px-3 py-2 text-sm outline-none focus:border-copper";

/** Connected badge + the "not connected" prompt or the fetch form. Shared by Home and the sidebar modal. */
export function GmailFetchForm({
  status, disabled, onFetch, onConnect,
}: {
  status: GmailStatus;
  disabled: boolean;
  onFetch: (params: GmailFetchParams) => void;
  onConnect: () => void;
}) {
  const [keywords, setKeywords] = useState("");
  const [after, setAfter] = useState("");
  const [before, setBefore] = useState("");
  const [limit, setLimit] = useState(25);

  if (!status.connected) {
    return (
      <>
        <p className="mt-2 text-sm text-muted">Connect your Gmail once, then fetch emails by subject and send replies from here.</p>
        <button type="button" onClick={onConnect}
          className="mt-3 rounded-full border border-line px-5 py-2 text-sm hover:bg-panel-2">
          {status.configured ? "Connect Gmail" : "Set up Gmail"}
        </button>
      </>
    );
  }
  return (
    <div className="mt-3 grid gap-3">
      <label className="block">
        <span className="mb-1 block text-xs tracking-wide text-muted uppercase">Subject contains</span>
        <input value={keywords} onChange={(e) => setKeywords(e.target.value)} className={fieldCls}
          placeholder="quest, interview, offer (any of these; blank = everything)" />
      </label>
      <div className="grid grid-cols-3 gap-3">
        <label className="block">
          <span className="mb-1 block text-xs tracking-wide text-muted uppercase">From</span>
          <input type="date" value={after} onChange={(e) => setAfter(e.target.value)} className={fieldCls} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs tracking-wide text-muted uppercase">To</span>
          <input type="date" value={before} onChange={(e) => setBefore(e.target.value)} className={fieldCls} />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs tracking-wide text-muted uppercase">Max</span>
          <input type="number" min={1} max={100} value={limit}
            onChange={(e) => setLimit(Math.max(1, Math.min(100, Number(e.target.value) || 25)))} className={fieldCls} />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button type="button" disabled={disabled}
          onClick={() => onFetch({ keywords, after, before, limit })}
          className="rounded-full bg-copper px-5 py-2 text-sm font-medium text-copper-deep disabled:opacity-50">
          {disabled ? "Working…" : "Fetch emails"}
        </button>
        <span className="text-xs text-muted">Unread or read, newest first. Your own sent mail is skipped.</span>
      </div>
    </div>
  );
}

export function ConnectedBadge({ connected }: { connected: boolean }) {
  return (
    <span className="flex items-center gap-2 text-xs text-muted">
      <i className={"size-2 rounded-full " + (connected ? "bg-good" : "bg-muted")} />
      {connected ? "Connected" : "Not connected"}
    </span>
  );
}

/** Sidebar popup with the same form as the Home page. */
export function GmailFetchModal({
  busy, onFetch, onConnect, onClose,
}: {
  busy: boolean;
  onFetch: (params: GmailFetchParams) => Promise<void>;
  onConnect: () => void;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [failed, setFailed] = useState(false);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    getGmail().then(setStatus).catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function fetchNow(params: GmailFetchParams) {
    setWorking(true);
    try {
      await onFetch(params); // errors show in the page's red banner
    } finally {
      setWorking(false);
      onClose();
    }
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-end bg-ink/70 sm:place-items-center" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="gmail-modal-title"
        className="flex max-h-[92dvh] w-full max-w-lg flex-col overflow-auto rounded-t-lg bg-panel p-6 text-fg shadow-2xl sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3">
          <h2 id="gmail-modal-title" className="flex items-center gap-2 font-display text-3xl">
            <Mail className="size-5 text-copper" />Pull from Gmail
          </h2>
          <div className="flex items-center gap-3">
            {status && <ConnectedBadge connected={status.connected} />}
            <button type="button" aria-label="Close" onClick={onClose} className="rounded-full p-2 text-muted hover:bg-panel-2">
              <X className="size-5" />
            </button>
          </div>
        </div>
        {failed && <p className="mt-3 text-sm text-bad">Could not reach the server to check Gmail.</p>}
        {!status && !failed && <p className="mt-3 text-sm text-muted">Checking Gmail…</p>}
        {status && (
          <GmailFetchForm status={status} disabled={busy || working}
            onFetch={(p) => void fetchNow(p)} onConnect={onConnect} />
        )}
      </div>
    </div>
  );
}