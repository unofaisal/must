import { useEffect, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { checkProviders, getSettings, putSettings } from "@/lib/api";
import type { CheckResult, SettingsPatch } from "@/lib/types";
import { GmailPanel } from "./GmailPanel";

const CHAT_PRESETS = [
  "nvidia/nemotron-3.5-lightning:free",
  "openai/gpt-4o-mini",
  "anthropic/claude-3.5-haiku",
  "google/gemini-2.0-flash-001",
  "meta-llama/llama-3.3-70b-instruct",
];
const DECIDE_PRESETS = ["respan/span-01-lite", "respan/mercury-decide:free"];

const inputCls = "w-full rounded-md border border-line bg-ink px-3 py-2.5 outline-none focus:border-copper";

function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs tracking-wide text-muted uppercase">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs leading-relaxed text-muted">{hint}</span>}
    </label>
  );
}

export function SettingsSheet({ onClose }: { onClose: () => void }) {
  const [apiKey, setApiKey] = useState("");
  const [keyHint, setKeyHint] = useState("");
  const [keySet, setKeySet] = useState(false);
  const [chatModel, setChatModel] = useState("");
  const [decideModel, setDecideModel] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [result, setResult] = useState<CheckResult | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => {
        setKeySet(s.api_key_set);
        setKeyHint(s.api_key_hint);
        setChatModel(s.chat_model);
        setDecideModel(s.decide_model);
        setCustomPrompt(s.custom_prompt);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoaded(true));
  }, []);

  function body(): SettingsPatch {
    const b: SettingsPatch = { chat_model: chatModel, decide_model: decideModel, custom_prompt: customPrompt };
    if (apiKey.trim()) b.api_key = apiKey.trim();
    return b;
  }

  async function persist() {
    const s = await putSettings(body());
    setKeySet(s.api_key_set);
    setKeyHint(s.api_key_hint);
    setApiKey("");
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(""); setOk(""); setResult(null);
    try {
      await persist();
      setOk("Settings saved. They apply to the next pipeline run.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setTesting(true); setError(""); setResult(null);
    try {
      await persist(); // the server tests with whatever it has stored
      setResult(await checkProviders());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not test the connection.");
    } finally {
      setTesting(false);
    }
  }

  async function clearKey() {
    try {
      const s = await putSettings({ api_key: "" });
      setKeySet(s.api_key_set);
      setKeyHint("");
      setApiKey("");
      setOk("API key cleared. Runs will use offline templates until a key is set.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not clear the key.");
    }
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-end bg-ink/70 sm:place-items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="flex max-h-[92dvh] w-full max-w-lg flex-col gap-4 overflow-auto rounded-t-lg bg-panel p-6 text-fg shadow-2xl sm:rounded-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 id="settings-title" className="font-display text-3xl">Settings</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="rounded-full p-2 text-muted hover:bg-panel-2">
            <X className="size-5" />
          </button>
        </div>

        {!loaded ? (
          <p className="py-2 text-sm text-muted">Loading…</p>
        ) : (
          <form onSubmit={save} className="flex flex-col gap-4">
            <Field
              label="OpenRouter API key"
              hint={
                <>
                  Stored in <code>data/settings.json</code> on the server. Leave blank to keep the current key.
                  {keySet && (
                    <button type="button" className="ml-1 text-copper underline" onClick={clearKey}>
                      Clear key
                    </button>
                  )}
                </>
              }
            >
              <input type="password" autoComplete="off" value={apiKey} className={inputCls}
                placeholder={keySet ? `Current key ${keyHint}` : "sk-or-…"}
                onChange={(e) => setApiKey(e.target.value)} />
            </Field>
            <Field label="Chat model (drafting)">
              <input list="chat-models" value={chatModel} placeholder="provider/model" className={inputCls}
                onChange={(e) => setChatModel(e.target.value)} />
              <datalist id="chat-models">{CHAT_PRESETS.map((m) => <option key={m} value={m} />)}</datalist>
            </Field>
            <Field label="Decision model (safety + grouping)">
              <input list="decide-models" value={decideModel} placeholder="provider/model" className={inputCls}
                onChange={(e) => setDecideModel(e.target.value)} />
              <datalist id="decide-models">{DECIDE_PRESETS.map((m) => <option key={m} value={m} />)}</datalist>
            </Field>
            <Field label="Custom drafting instructions">
              <textarea rows={4} value={customPrompt} className={inputCls + " resize-y"}
                placeholder="Optional. Appended to the system prompt for every draft, e.g. tone, sign-off, or what never to promise."
                onChange={(e) => setCustomPrompt(e.target.value)} />
            </Field>

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
                <p>
                  <strong>Connection</strong>{" "}
                  {result.key_present ? `Key present (${result.key_hint})` : "No API key — offline mode"}
                </p>
                {result.models && (
                  <p className="mt-1 text-xs text-muted">
                    Models: chat <code>{result.models.chat}</code>, decide <code>{result.models.decide}</code>
                  </p>
                )}
                {(["chat", "decide"] as const).map((k) => {
                  const r = result[k];
                  if (!r) return null;
                  return (
                    <p key={k} className={"mt-1 " + (r.ok ? "text-good" : "text-bad")}>
                      {k}: {r.ok ? `ok (${r.ms} ms)` : r.error}
                    </p>
                  );
                })}
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2">
              <button type="button" onClick={test} disabled={busy || testing}
                className="rounded-full border border-line px-4 py-2 text-sm disabled:opacity-50">
                {testing ? "Testing…" : "Test connection"}
              </button>
              <div className="flex gap-2">
                <button type="button" onClick={onClose} disabled={busy} className="rounded-full px-4 py-2 text-sm text-muted">
                  Close
                </button>
                <button type="submit" disabled={busy}
                  className="rounded-full bg-copper px-5 py-2 text-sm font-medium text-copper-deep disabled:opacity-50">
                  {busy ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </form>
        )}
        {loaded && <GmailPanel />}
      </div>
    </div>
  );
}
