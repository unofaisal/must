import { useEffect, useRef, useState } from "react";
import { patchItem, sendItem } from "./api.js";
import { groupName } from "./groups.js";

const PLACEHOLDER = /\[([^\[\]]+)\]/g;

function sourceNote(item) {
  if (item.kind === "quarantined") return "";
  if (item.draft_source === "template") return "Template reply. No model was used.";
  if (item.draft_source === "template (fallback)") return "Template reply. The model failed on this message.";
  return "Written by the model. Check every fact before approving.";
}

function statusText(item) {
  if (item.status === "approved") return "Approved";
  if (item.status === "rejected") return "Rejected";
  if (item.status === "sent") {
    const when = new Date(item.sent_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
    return `Sent ${when}`;
  }
  return "To review";
}

export default function ItemRow({ item, onChange }) {
  const [text, setText] = useState(item.draft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const latest = useRef(0); // only the newest request may update the row

  useEffect(() => setText(item.draft), [item.draft]);

  const locked = item.status === "sent";
  const missing = [...text.matchAll(PLACEHOLDER)].map((m) => m[1]);
  const canApprove = text.trim() !== "" && missing.length === 0;
  const quarantined = item.kind === "quarantined";
  const also = item.labels.slice(1).map(groupName);

  async function call(request, { blocking = true } = {}) {
    const id = ++latest.current;
    if (blocking) setBusy(true);
    setError("");
    try {
      const updated = await request();
      if (id === latest.current) onChange(updated);
    } catch (e) {
      if (id === latest.current) setError(e.message);
    } finally {
      if (blocking && id === latest.current) setBusy(false);
    }
  }

  // Saving on blur must never disable the buttons, or a click on Approve gets lost.
  const saveDraft = () => {
    if (!locked && text !== item.draft) call(() => patchItem(item.key, { draft: text }), { blocking: false });
  };
  const approve = () => call(() => patchItem(item.key, { draft: text, status: "approved" }));
  const reject = () => call(() => patchItem(item.key, { status: "rejected" }));
  const reopen = () => call(() => patchItem(item.key, { status: "pending" }));
  const send = () => call(() => sendItem(item.key));

  const approveHint = text.trim() === ""
    ? "Write a reply to approve."
    : missing.length
      ? `Fill in ${missing.map((m) => `[${m}]`).join(", ")} before approving.`
      : "";

  return (
    <article className="item" data-status={item.status} data-flagged={quarantined || undefined}>
      <header className="item-head">
        <div>
          <span className="who">{item.sender || "Unknown sender"}</span>
          {item.email && <span className="addr">{item.email}</span>}
        </div>
        <span className="state">{statusText(item)}</span>
      </header>

      <div className="original">
        <h3>{item.subject || "(no subject)"}</h3>
        <p>{item.body}</p>
        {also.length > 0 && <p className="also">Also asks about: {also.join(", ")}</p>}
      </div>

      <div className="reply">
        {quarantined && (
          <ul className="reasons">
            {item.reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        )}
        <label className="visually-hidden" htmlFor={`reply-${item.key}`}>
          Reply to {item.sender}
        </label>
        <textarea
          id={`reply-${item.key}`}
          value={text}
          readOnly={locked}
          placeholder={quarantined ? "No draft was written. Write your own reply, or reject to dismiss." : ""}
          onChange={(e) => setText(e.target.value)}
          onBlur={saveDraft}
        />
        {item.status === "pending" && missing.length > 0 && (
          <p className="warn">Fill in {missing.map((m) => `[${m}]`).join(", ")} before approving.</p>
        )}
        {sourceNote(item) && <p className="note">{sourceNote(item)}</p>}
      </div>

      <footer className="item-foot">
        {error && <p className="error" role="alert">{error}</p>}
        {item.status === "pending" && (
          <>
            <button className="btn" onClick={reject} disabled={busy}>Reject</button>
            <button className="btn primary" onClick={approve} disabled={busy || !canApprove}
                    title={approveHint}>Approve</button>
          </>
        )}
        {item.status === "approved" && (
          <>
            <button className="btn" onClick={reopen} disabled={busy}>Undo approval</button>
            <button className="btn primary" onClick={send} disabled={busy}>Send reply</button>
          </>
        )}
        {item.status === "rejected" && (
          <button className="btn" onClick={reopen} disabled={busy}>Restore</button>
        )}
      </footer>
    </article>
  );
}
