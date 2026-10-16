import { useCallback, useMemo, useRef, useState, type DragEvent } from "react";
import { Link, Navigate, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { Download, FileUp, Mail, History as HistoryIcon, Home as HomeIcon, ListChecks, Settings as Cog, Workflow, X } from "lucide-react";
import { ActionsCtx, type Actions } from "../lib/actions";
import { EXPORT_URL } from "../lib/api";
import { isOpen } from "../lib/groups";
import { useStore } from "../lib/store";
import type { GmailFetchParams } from "../lib/types";
import { GmailFetchModal } from "./GmailFetchForm";
import { SettingsSheet } from "./Settings";

const navCls = "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm text-muted hover:bg-panel-2 hover:text-fg";
const navActive = { className: "flex shrink-0 items-center gap-2 rounded-md bg-panel-2 px-3 py-2 text-sm text-fg" };

export function Shell() {
  const { batch, history, ready, starting, running, error, setError, begin, beginGmail, openBatch, settingsOpen, setSettingsOpen } = useStore();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const fileRef = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [gmailOpen, setGmailOpen] = useState(false);
  const [hidden, setHidden] = useState<string[]>([]); // provider problems the user dismissed

  const openId = batch.batch?.id;
  const start = useCallback(
    async (source: File | "sample") => {
      if (await begin(source)) void navigate({ to: "/pipeline" });
      if (fileRef.current) fileRef.current.value = "";
    },
    [begin, navigate],
  );
  const startGmail = useCallback(
    async (params: GmailFetchParams) => {
      if (await beginGmail(params)) void navigate({ to: "/pipeline" });
    },
    [beginGmail, navigate],
  );
  const openPast = useCallback(
    async (id: string) => {
      if (id === openId || (await openBatch(id))) void navigate({ to: "/review" });
    },
    [openId, openBatch, navigate],
  );
  const choose = useCallback(() => fileRef.current?.click(), []);
  const actions = useMemo<Actions>(() => ({ choose, start, startGmail, openPast }), [choose, start, startGmail, openPast]);
  const onFile = (file?: File) => { if (file) void start(file); };

  const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");
  const drag = {
    onDragEnter: (e: DragEvent) => { if (hasFiles(e)) { dragDepth.current += 1; setDragging(true); } },
    onDragOver: (e: DragEvent) => { if (hasFiles(e)) e.preventDefault(); },
    onDragLeave: (e: DragEvent) => { if (hasFiles(e) && --dragDepth.current <= 0) { dragDepth.current = 0; setDragging(false); } },
    onDrop: (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      dragDepth.current = 0;
      setDragging(false);
      onFile(e.dataTransfer.files[0]);
    },
  };

  if (!ready) return <div className="h-dvh bg-ink" />;

  const items = batch.items;
  const onHome = pathname === "/";
  const needsBatch = pathname === "/review" || pathname === "/pipeline";
  const open = items.filter(isOpen).length;
  const exportable = items.filter((i) => i.status === "approved" || i.status === "sent").length;
  const handled = items.filter((i) => i.status !== "pending").length;

  const pe = batch.run.provider_errors;
  const calls = (n: number) => `${n} ${n === 1 ? "call" : "calls"}`;
  const problems: string[] = [];
  if (pe.chat?.errors) problems.push(`Drafting: ${calls(pe.chat.errors)} to the model failed, so those replies are templates. Last error: ${pe.chat.last}`);
  if (pe.decide?.errors) problems.push(`Decision model: ${calls(pe.decide.errors)} failed. Grouping fell back to keyword rules, and safety held those emails for a human. Last error: ${pe.decide.last}`);
  const visible = problems.filter((p) => !hidden.includes(p));

  const dismissBtn = "ml-auto flex shrink-0 items-center gap-1 rounded px-1.5 underline-offset-2 hover:underline";
  const banners = (showError: boolean) =>
    (showError && error) || visible.length > 0 ? (
      <div role="alert" className="z-30 flex shrink-0 flex-col gap-1 bg-bad px-4 py-2 text-sm text-sheet">
        {showError && error && (
          <p className="flex items-start gap-3">
            <span>{error}</span>
            <button type="button" className={dismissBtn} onClick={() => setError("")} aria-label="Dismiss error"><X className="size-4" />Dismiss</button>
          </p>
        )}
        {visible.map((p) => (
          <p key={p} className="flex items-start gap-3">
            <span>{p}</span>
            <button type="button" className={dismissBtn} onClick={() => setHidden((h) => [...h, p])} aria-label="Dismiss warning"><X className="size-4" />Dismiss</button>
          </p>
        ))}
      </div>
    ) : null;

  return (
    <ActionsCtx.Provider value={actions}>
      <div {...drag} className="min-h-dvh bg-ink text-fg">
        <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" tabIndex={-1}
          onChange={(e) => onFile(e.target.files?.[0])} />

        {needsBatch && !items.length && <Navigate to="/" />}

        {onHome ? (
          <>
            {banners(false)}
            <Outlet />
          </>
        ) : (
          <div className="flex h-dvh min-h-0 flex-col md:flex-row">
            <aside className="flex shrink-0 flex-col gap-3 border-b border-line bg-panel p-3 md:w-56 md:border-r md:border-b-0 md:p-4">
              <div className="flex items-center justify-between md:block md:px-1 md:pt-3">
                <Link to="/" className="block font-display text-2xl tracking-tight hover:text-copper" title="Back to the home page">Desk</Link>
                <p className="hidden text-xs tracking-wide text-muted uppercase md:block">Candidate mail</p>
                <span className="text-xs text-muted md:hidden">{batch.mode === "live" ? "Live models" : "Offline"}</span>
              </div>

              <nav aria-label="Views" className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
                <Link to="/" className={navCls}><HomeIcon className="size-4" />Home</Link>
                {items.length > 0 && (
                  <>
                    <Link to="/review" activeProps={navActive} inactiveProps={{ className: navCls }}>
                      <ListChecks className="size-4" />Review<span className="ml-auto text-xs opacity-70">{open}</span>
                    </Link>
                    <Link to="/pipeline" activeProps={navActive} inactiveProps={{ className: navCls }}>
                      <Workflow className="size-4" />Pipeline
                      {running && <i aria-label="running" className="ml-auto size-2 animate-pulse rounded-full bg-copper" />}
                    </Link>
                  </>
                )}
                <Link to="/history" activeProps={navActive} inactiveProps={{ className: navCls }}>
                  <HistoryIcon className="size-4" />Past work
                  {history.length > 0 && <span className="ml-auto text-xs opacity-70">{history.length}</span>}
                </Link>
              </nav>

              <div className="hidden flex-col gap-2 md:flex">
                <button type="button" onClick={choose} disabled={starting || running}
                  className="flex items-center justify-center gap-2 rounded-md bg-copper px-3 py-2.5 text-sm font-medium text-copper-deep disabled:opacity-50">
                  <FileUp className="size-4" />Upload CSV
                </button>
                <button type="button" onClick={() => void start("sample")} disabled={starting || running}
                  className="rounded-md border border-line px-3 py-2.5 text-sm disabled:opacity-50">Sample inbox</button>
                <button type="button" onClick={() => setGmailOpen(true)} disabled={starting || running}
                  className="flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2.5 text-sm hover:bg-panel-2 disabled:opacity-50">
                  <Mail className="size-4" />Pull from Gmail
                </button>
                {exportable > 0 ? (
                  <a href={EXPORT_URL} download className="flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2.5 text-sm hover:bg-panel-2">
                    <Download className="size-4" />Export ({exportable})
                  </a>
                ) : (
                  <button type="button" disabled title="Approve a reply to export it."
                    className="flex items-center justify-center gap-2 rounded-md border border-line px-3 py-2.5 text-sm opacity-40">
                    <Download className="size-4" />Export
                  </button>
                )}
              </div>

              {items.length > 0 && (
                <div className="hidden px-1 md:block">
                  <p className="truncate text-xs text-muted" title={batch.batch?.name}>{batch.batch?.name || "Current batch"}</p>
                  <p className="font-display text-3xl">{handled}<span className="text-base text-muted"> / {items.length}</span></p>
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-panel-2">
                    <div className="h-full bg-copper transition-[width] duration-300" style={{ width: `${(handled / items.length) * 100}%` }} />
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-muted">
                    {batch.mode === "live" ? "Live models are drafting." : "Offline: template drafts. Add a key in Settings for live models."}
                    {batch.run.demo_delay_ms > 0 && ` Demo delay +${batch.run.demo_delay_ms} ms.`}
                  </p>
                </div>
              )}

              <button type="button" onClick={() => setSettingsOpen(true)}
                className="mt-auto hidden items-center gap-2 rounded-md px-2 py-2 text-sm text-muted hover:bg-panel-2 hover:text-fg md:flex">
                <Cog className="size-4" />Settings
              </button>
              <div className="flex gap-2 md:hidden">
                <button type="button" onClick={choose} disabled={starting || running} className="rounded-md border border-line px-3 py-1.5 text-xs disabled:opacity-50">Upload</button>
                <button type="button" onClick={() => setGmailOpen(true)} disabled={starting || running} className="rounded-md border border-line px-3 py-1.5 text-xs disabled:opacity-50">Gmail</button>
                {exportable > 0 && <a href={EXPORT_URL} download className="rounded-md border border-line px-3 py-1.5 text-xs">Export ({exportable})</a>}
                <button type="button" onClick={() => setSettingsOpen(true)} className="ml-auto rounded-md px-3 py-1.5 text-xs text-muted">Settings</button>
              </div>
            </aside>

            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              {banners(true)}
              <div className="min-h-0 flex-1">
                <Outlet />
              </div>
            </div>
          </div>
        )}

        {dragging && (
          <div aria-hidden="true" className="fixed inset-0 z-50 grid place-items-center bg-ink/85 font-display text-4xl text-copper">
            Drop the CSV to start
          </div>
        )}
        {gmailOpen && (
          <GmailFetchModal busy={starting || running} onFetch={startGmail} onClose={() => setGmailOpen(false)}
            onConnect={() => { setGmailOpen(false); setSettingsOpen(true); }} />
        )}
        {settingsOpen && <SettingsSheet onClose={() => setSettingsOpen(false)} />}
      </div>
    </ActionsCtx.Provider>
  );
}