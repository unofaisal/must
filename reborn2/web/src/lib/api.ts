import type {
  Batch, CheckResult, GmailConfigPatch, GmailFetchParams, GmailStatus, GmailTest,
  HistoryEntry, Item, Settings, SettingsPatch, Status,
} from "./types";

async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let message = `The server returned an error (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = "The request was not valid.";
    } catch {
      /* keep the generic message */
    }
    throw new Error(message);
  }
  return res;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const EXPORT_URL = "/api/export";

export const getBatch = async (): Promise<Batch> => (await request("/api/items")).json();

export async function uploadCsv(file: File): Promise<Batch> {
  const form = new FormData();
  form.append("file", file);
  return (await request("/api/upload", { method: "POST", body: form })).json();
}

export const startSample = async (): Promise<Batch> =>
  (await request("/api/sample", { method: "POST" })).json();

export const patchItem = async (
  key: string,
  body: { draft?: string; status?: Exclude<Status, "sent"> },
): Promise<Item> => (await request(`/api/items/${key}`, json("PATCH", body))).json();

export const sendItem = async (key: string): Promise<Item> =>
  (await request(`/api/items/${key}/send`, { method: "POST" })).json();

export const getHistory = async (): Promise<HistoryEntry[]> => (await request("/api/history")).json();

export const openHistory = async (id: string): Promise<Batch> =>
  (await request(`/api/history/${encodeURIComponent(id)}/open`, { method: "POST" })).json();

export const deleteHistory = async (id: string): Promise<Batch> =>
  (await request(`/api/history/${encodeURIComponent(id)}`, { method: "DELETE" })).json();

export const getSettings = async (): Promise<Settings> => (await request("/api/settings")).json();

export const putSettings = async (body: SettingsPatch): Promise<Settings> =>
  (await request("/api/settings", json("PUT", body))).json();

export const getGmail = async (): Promise<GmailStatus> => (await request("/api/gmail")).json();

export const putGmail = async (body: GmailConfigPatch): Promise<GmailStatus> =>
  (await request("/api/gmail/config", json("PUT", body))).json();

export const disconnectGmail = async (): Promise<GmailStatus> =>
  (await request("/api/gmail/disconnect", { method: "POST" })).json();

export const testGmail = async (): Promise<GmailTest> =>
  (await request("/api/gmail/test", { method: "POST" })).json();

export const fetchGmail = async (body: GmailFetchParams): Promise<Batch> =>
  (await request("/api/gmail/fetch", json("POST", body))).json();

/** Sends the browser to Google's Allow screen; Google returns it to this page. */
export const GMAIL_CONNECT_URL = () =>
  `/api/gmail/authorize?return_to=${encodeURIComponent(window.location.origin)}`;

export const checkProviders = async (): Promise<CheckResult> =>
  (await request("/api/check")).json();
