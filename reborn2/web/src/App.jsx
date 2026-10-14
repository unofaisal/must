import { useEffect, useMemo, useRef, useState } from "react";
import { getBatch, uploadCsv } from "./api.js";
import { GROUPS, groupOf } from "./groups.js";
import ItemRow from "./ItemRow.jsx";

const TABS = [
  { key: "open", label: "Open", match: (i) => i.status === "pending" || i.status === "approved" },
  { key: "sent", label: "Sent", match: (i) => i.status === "sent" },
  { key: "rejected", label: "Rejected", match: (i) => i.status === "rejected" },
  { key: "all", label: "All", match: () => true },
];

export default function App() {
  const [items, setItems] = useState([]);
  const [mode, setMode] = useState("offline");
  const [group, setGroup] = useState("all");
  const [tab, setTab] = useState("open");
  const [loading, setLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [ready, setReady] = useState(false);
  const fileInput = useRef(null);

  useEffect(() => {
    getBatch()
      .then((b) => { setItems(b.items); setMode(b.mode); })
      .catch(() => setUploadError("Could not reach the server. Start it with: uvicorn api.main:app --reload"))
      .finally(() => setReady(true));
  }, []);

  async function handleFile(file) {
    if (!file) return;
    if (items.length && !window.confirm(
      "Replace the current batch? Replies you have not sent will be lost. Export approved replies first if you need them.")) return;
    setLoading(true);
    setUploadError("");
    try {
      const b = await uploadCsv(file);
      setItems(b.items);
      setMode(b.mode);
      setGroup("all");
      setTab("open");
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setLoading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  const replaceItem = (updated) => setItems((all) => all.map((i) => (i.key === updated.key ? updated : i)));

  const counts = useMemo(() => {
    const open = {};
    const tabs = {};
    for (const i of items) {
      if (TABS[0].match(i)) open[groupOf(i)] = (open[groupOf(i)] || 0) + 1;
      for (const t of TABS) if (t.match(i)) tabs[t.key] = (tabs[t.key] || 0) + 1;
    }
    return { open, tabs };
  }, [items]);

  const exportable = items.filter((i) => i.status === "approved" || i.status === "sent").length;
  const tabMatch = TABS.find((t) => t.key === tab).match;
  const sections = GROUPS
    .map((g) => ({ ...g, rows: items.filter((i) => groupOf(i) === g.key && tabMatch(i)) }))
    .filter((s) => s.rows.length && (group === "all" || group === s.key));
  const navGroups = GROUPS.filter((g) => items.some((i) => groupOf(i) === g.key));

  const picker = (
    <input ref={fileInput} type="file" accept=".csv,text/csv" className="visually-hidden"
           onChange={(e) => handleFile(e.target.files[0])} tabIndex={-1} />
  );

  if (!items.length) {
    return (
      <main className="intake">
        {picker}
        <h1>Upload candidate emails</h1>
        <p>
          Choose a CSV with the columns <code>id</code>, <code>sender</code>, <code>subject</code> and{" "}
          <code>body</code>. Add an <code>email</code> column to match each sender to a candidate record.
          Nothing is sent until you approve it.
        </p>
        <div className="drop" onDragOver={(e) => e.preventDefault()}
             onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}>
          <button className="btn primary" onClick={() => fileInput.current.click()} disabled={loading || !ready}>
            {loading ? "Reading emails and drafting replies…" : "Choose a CSV file"}
          </button>
          <span>or drop it here</span>
        </div>
        {loading && <p className="note" role="status">With live models this can take a minute.</p>}
        {uploadError && <p className="error" role="alert">{uploadError}</p>}
      </main>
    );
  }

  return (
    <>
      {picker}
      <header className="topbar">
        <span className="brand">Inbox helper</span>
        <span className="mode">{mode === "live" ? "Live models" : "Offline mode: template replies"}</span>
        <button className="btn" onClick={() => fileInput.current.click()} disabled={loading}>
          {loading ? "Working…" : "Upload new CSV"}
        </button>
        {exportable > 0
          ? <a className="btn primary" href="/api/export" download>Export approved ({exportable})</a>
          : <button className="btn primary" disabled title="Approve a reply to export it.">Export approved (0)</button>}
      </header>

      <div className="shell">
        <nav className="nav" aria-label="Groups">
          <button aria-current={group === "all"} onClick={() => setGroup("all")}>
            <span>All groups</span><span className="count">{counts.tabs.open || 0}</span>
          </button>
          {navGroups.map((g) => (
            <button key={g.key} aria-current={group === g.key} data-flag={g.key === "quarantined" || undefined}
                    onClick={() => setGroup(g.key)}>
              <span>{g.label}</span><span className="count">{counts.open[g.key] || 0}</span>
            </button>
          ))}
        </nav>

        <main className="main">
          {uploadError && <p className="error" role="alert">{uploadError}</p>}
          <div className="tabs" role="tablist">
            {TABS.map((t) => (
              <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>
                {t.label} <span className="count">{counts.tabs[t.key] || 0}</span>
              </button>
            ))}
          </div>

          {sections.length === 0 && (
            <p className="empty">
              {tab === "open" ? "Nothing left to review here." : "Nothing in this view yet."}
            </p>
          )}
          {sections.map((s) => (
            <section key={s.key} className="section" data-flag={s.key === "quarantined" || undefined}>
              <h2>{s.label} <span className="count">{s.rows.length}</span></h2>
              {s.hint && <p className="hint">{s.hint}</p>}
              {s.rows.map((i) => <ItemRow key={i.key} item={i} onChange={replaceItem} />)}
            </section>
          ))}
        </main>
      </div>
    </>
  );
}
