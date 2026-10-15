import { useEffect, useState, type ReactNode } from "react";
import { disconnectGmail, getGmail, GMAIL_CONNECT_URL, putGmail, testGmail } from "@/lib/api";
import { useStore } from "@/lib/store";
import type { GmailConfigPatch, GmailStatus, GmailTest } from "@/lib/types";

const inputCls = "w-full rounded-md border border-line bg-ink px-3 py-2.5 text-sm outline-none focus:border-copper";

function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs tracking-wide text-muted uppercase">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs leading-relaxed text-muted">{hint}</span>}
    </label>
  );
}

/** Gmail connection: paste the Google client ID and secret once, then press Connect Gmail. */
export function GmailPanel() {
  const { gmailNotice, clearGmailNotice } = useStore();
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [clientId, setClientId] = useState("");
  const [secret, setSecret] = useState("");
  const [mcpUrl, setMcpUrl] = useState("");
  const [scopes, setScopes] = useState("");
  const [redirectUri, setRedirectUri] = useState("");
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [result, setResult] = useState<GmailTest | null>(null);

  function adopt(s: GmailStatus) {
    setStatus(s);
    setClientId(s.client_id);
    setMcpUrl(s.mcp_url);
    setScopes(s.scopes);
    setRedirectUri(s.redirect_uri);
  }

  useEffect(() => {
    getGmail().then(adopt).catch((e: Error) => setError(e.message));
  }, []);

  function body(): GmailConfigPatch {
    const b: GmailConfigPatch = { client_id: clientId, mcp_url: mcpUrl, scopes, redirect_uri: redirectUri };
    if (secret.trim()) b.client_secret = secret.trim();
    return b;
  }

  async function persist(): Promise<GmailStatus> {
    const s = await putGmail(body());
    adopt(s);
    setSecret("");
    return s;
  }

  async function save() {
    setBusy(true); setError(""); setOk(""); setResult(null); clearGmailNotice();
    try {
      await persist();
      setOk("Gmail settings saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function connect() {
    setBusy(true); setError(""); setOk(""); clearGmailNotice();
    try {
      const s = await persist();
      if (!s.configured) {
        setError("Paste the client ID and client secret first.");
        setBusy(false);
        return;
      }
      window.location.href = GMAIL_CONNECT_URL(); // Google's Allow screen, then back here
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the sign-in.");
      setBusy(false);
    }
  }

  async function test() {
    setTesting(true); setError(""); setOk(""); setResult(null); clearGmailNotice();
    try {
      setResult(await testGmail());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not test the connection.");
    } finally {
      setTesting(false);
    }
  }

  async function disconnect() {
    setError(""); setOk(""); setResult(null); clearGmailNotice();
    try {
      adopt(await disconnectGmail());
      setOk("Gmail disconnected. The saved login was removed from this computer.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not disconnect.");
    }
  }

  const pill = "rounded-full border border-line px-4 py-2 text-sm disabled:opacity-50";

  return (
    <section className="mt-2 flex flex-col gap-4 border-t border-line pt-5" aria-labelledby="gmail-title">
      <div className="flex items-center justify-between gap-3">
        <h3 id="gmail-title" className="font-display text-2xl">Gmail</h3>
        {status && (
          <span className="flex items-center gap-2 text-xs text-muted">
            <i className={"size-2 rounded-full " + (status.connected ? "bg-good" : "bg-muted")} />
            {status.connected ? "Connected" : status.configured ? "Ready to connect" : "Not set up"}
          </span>
        )}
      </div>

      <details className="rounded-md border border-line bg-ink px-3 py-2.5 text-sm">
        <summary className="cursor-pointer">First time? Four steps in Google Cloud (about 10 minutes, once)</summary>
        <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-muted">
          <li>Open <code>console.cloud.google.com</code> and create a project.</li>
          <li>APIs &amp; Services, Library: enable <strong>Gmail API</strong> and <strong>Gmail MCP API</strong>.</li>
          <li>OAuth consent screen (Google Auth platform): choose External, add your own Gmail address under <strong>Test users</strong>, and add the scopes <code>gmail.readonly</code> and <code>gmail.compose</code>.</li>
          <li>Credentials, Create credentials, OAuth client ID, type <strong>Web application</strong>. Under Authorized redirect URIs add <code className="break-all">{redirectUri || "http://localhost:8000/api/gmail/callback"}</code>. Copy the Client ID and Client secret into the boxes below.</li>
        </ol>
        <p className="mt-2 text-xs text-muted">
          While the Google app is in Testing mode, Google asks you to sign in again about every 7 days. Just press Connect Gmail.
        </p>
      </details>

      <Field label="Google client ID">
        <input value={clientId} autoComplete="off" onChange={(e) => setClientId(e.target.value)}
          placeholder="1234-abc.apps.googleusercontent.com" className={inputCls} />
      </Field>
      <Field label="Google client secret"
        hint={<>Stored in <code>data/gmail.json</code> on this computer. Leave blank to keep the current one.</>}>
        <input type="password" autoComplete="off" value={secret} onChange={(e) => setSecret(e.target.value)}
          placeholder={status?.secret_set ? `Current secret ${status.secret_hint}` : "GOCSPX-…"} className={inputCls} />
      </Field>

      <details className="text-sm">
        <summary className="cursor-pointer text-muted">Advanced (defaults are right for Google's Gmail server)</summary>
        <div className="mt-3 flex flex-col gap-4">
          <Field label="MCP server URL">
            <input value={mcpUrl} onChange={(e) => setMcpUrl(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Redirect URI" hint="Must match, character for character, the one you added in Google Cloud.">
            <input value={redirectUri} onChange={(e) => setRedirectUri(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Scopes (space separated)">
            <input value={scopes} onChange={(e) => setScopes(e.target.value)} className={inputCls} />
          </Field>
        </div>
      </details>

      {gmailNotice && (
        <p role="status" className={"flex items-start gap-3 text-sm " + (gmailNotice.ok ? "text-good" : "text-bad")}>
          <span>{gmailNotice.text}</span>
          <button type="button" className="ml-auto shrink-0 underline" onClick={clearGmailNotice}>Dismiss</button>
        </p>
      )}
      {error && (
        <p role="alert" className="flex items-start gap-3 text-sm text-bad">
          <span>{error}</span>
          <button type="button" className="ml-auto shrink-0 underline" onClick={() => setError("")}>Dismiss</button>
        </p>
      )}
      {ok && (
        <p role="status" className="flex items-start gap-3 text-sm text-good">
          <span>{ok}</span>
          <button type="button" className="ml-auto shrink-0 underline" onClick={() => setOk("")}>Dismiss</button>
        </p>
      )}
      {result && (
        <div className="rounded-md border border-line bg-ink p-3 text-sm">
          <p className={result.ok ? "text-good" : "text-bad"}>
            {result.ok ? "Connected. The Gmail server has what this app needs." : `Missing tools: ${result.missing.join(", ")}`}
          </p>
          <p className="mt-1 text-xs text-muted">Tools offered: {result.tools.join(", ") || "none"}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={connect} disabled={busy}
          className="rounded-full bg-copper px-5 py-2 text-sm font-medium text-copper-deep disabled:opacity-50">
          {status?.connected ? "Reconnect Gmail" : "Connect Gmail"}
        </button>
        <button type="button" onClick={save} disabled={busy} className={pill}>Save</button>
        <button type="button" onClick={test} disabled={busy || testing || !status?.connected} className={pill}>
          {testing ? "Testing…" : "Test"}
        </button>
        {status?.connected && (
          <button type="button" onClick={disconnect} className="ml-auto px-2 py-2 text-sm text-muted underline">Disconnect</button>
        )}
      </div>
    </section>
  );
}
