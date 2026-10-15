import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { deleteHistory, fetchGmail, getBatch, getHistory, openHistory, startSample, uploadCsv } from "./api";
import type { Batch, GmailFetchParams, HistoryEntry, Item } from "./types";

const EMPTY: Batch = {
  mode: "offline",
  batch: null,
  run: { state: "idle", total: 0, done: 0, elapsed: 0, demo_delay_ms: 0, provider_errors: {} },
  items: [],
};

interface Store {
  batch: Batch;
  ready: boolean;
  starting: boolean;
  running: boolean;
  error: string;
  setError: (message: string) => void;
  selected: string | null;
  select: (key: string | null) => void;
  /** Starts a run from a CSV file or the bundled sample. Resolves true if a run began. */
  begin: (source: File | "sample") => Promise<boolean>;
  /** Pulls matching emails from Gmail and starts a run. Resolves true if a run began. */
  beginGmail: (params: GmailFetchParams) => Promise<boolean>;
  /** Result of the last "Connect Gmail" sign-in, shown once in Settings. */
  gmailNotice: { ok: boolean; text: string } | null;
  clearGmailNotice: () => void;
  history: HistoryEntry[];
  refreshHistory: () => Promise<void>;
  /** Reopens a saved batch. Resolves true if it is now the open batch. */
  openBatch: (id: string) => Promise<boolean>;
  removeBatch: (id: string) => Promise<void>;
  replaceItem: (updated: Item) => void;
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
}

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const value = useContext(Ctx);
  if (!value) throw new Error("useStore must be used inside <StoreProvider>");
  return value;
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [batch, setBatch] = useState<Batch>(EMPTY);
  const [ready, setReady] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [selected, select] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const polling = useRef(false);
  const [gmailNotice, setGmailNotice] = useState<{ ok: boolean; text: string } | null>(null);

  // Google sends the browser back with ?gmail=connected (or =error). Show it in Settings once.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("gmail");
    if (!result) return;
    setGmailNotice(
      result === "connected"
        ? { ok: true, text: "Gmail is connected. Press Test to check the connection." }
        : { ok: false, text: params.get("gmail_message") || "Gmail sign-in did not finish. Try again." },
    );
    setSettingsOpen(true);
    window.history.replaceState(null, "", window.location.pathname + window.location.hash);
  }, []);

  const running = batch.run.state === "running";
  const hasItems = batch.items.length > 0;

  // Restore the batch the server is holding (it survives refreshes and restarts).
  useEffect(() => {
    getBatch()
      .then((b) => {
        setBatch(b);
        select(b.items[0]?.key ?? null);
      })
      .catch(() => setError("Could not reach the server. Start it with: uvicorn api.main:app --reload"))
      .finally(() => setReady(true));
  }, []);

  // While a run is in progress, poll the server for stage updates.
  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(() => {
      if (polling.current) return;
      polling.current = true;
      getBatch()
        .then(setBatch)
        .catch(() => {})
        .finally(() => {
          polling.current = false;
        });
    }, 500);
    return () => clearInterval(timer);
  }, [running]);

  const begin = useCallback(
    async (source: File | "sample"): Promise<boolean> => {
      if (
        hasItems &&
        !running &&
        !window.confirm(
          "Replace the current batch? Replies you have not sent will be lost. Export approved replies first if you need them.",
        )
      )
        return false;
      setStarting(true);
      setError("");
      try {
        const b = source === "sample" ? await startSample() : await uploadCsv(source);
        setBatch(b);
        select(b.items[0]?.key ?? null);
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not start the run.");
        return false;
      } finally {
        setStarting(false);
      }
    },
    [hasItems, running],
  );

  const beginGmail = useCallback(
    async (params: GmailFetchParams): Promise<boolean> => {
      if (
        hasItems &&
        !running &&
        !window.confirm(
          "Replace the current batch? Replies you have not sent will be lost. Export approved replies first if you need them.",
        )
      )
        return false;
      setStarting(true);
      setError("");
      try {
        const b = await fetchGmail(params);
        setBatch(b);
        select(b.items[0]?.key ?? null);
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not fetch from Gmail.");
        return false;
      } finally {
        setStarting(false);
      }
    },
    [hasItems, running],
  );

  const clearGmailNotice = useCallback(() => setGmailNotice(null), []);

  const refreshHistory = useCallback(async () => {
    try {
      setHistory(await getHistory());
    } catch {
      /* the list is a convenience; the page works without it */
    }
  }, []);

  // Past work changes when a run finishes, a batch is opened, or one is deleted.
  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory, batch.run.state, batch.batch?.id]);

  const openBatch = useCallback(async (id: string): Promise<boolean> => {
    setError("");
    try {
      const b = await openHistory(id);
      setBatch(b);
      select(b.items[0]?.key ?? null);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open that batch.");
      return false;
    }
  }, []);

  const removeBatch = useCallback(
    async (id: string) => {
      setError("");
      try {
        const b = await deleteHistory(id);
        setBatch(b);
        if (!b.items.length) select(null);
        await refreshHistory();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not delete that batch.");
      }
    },
    [refreshHistory],
  );

  const replaceItem = useCallback((updated: Item) => {
    setBatch((b) => ({ ...b, items: b.items.map((i) => (i.key === updated.key ? updated : i)) }));
  }, []);

  const value = useMemo<Store>(
    () => ({
      batch, ready, starting, running, error, setError, selected, select,
      begin, beginGmail, gmailNotice, clearGmailNotice,
      history, refreshHistory, openBatch, removeBatch, replaceItem, settingsOpen, setSettingsOpen,
    }),
    [batch, ready, starting, running, error, selected, begin, beginGmail, gmailNotice, clearGmailNotice,
      history, refreshHistory, openBatch, removeBatch, replaceItem, settingsOpen],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
