async function request(path, options) {
  const res = await fetch(path, options);
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

const json = (body) => ({
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export async function getBatch() {
  return (await request("/api/items")).json();
}

export async function uploadCsv(file) {
  const form = new FormData();
  form.append("file", file);
  return (await request("/api/upload", { method: "POST", body: form })).json();
}

export async function patchItem(key, body) {
  return (await request(`/api/items/${key}`, json(body))).json();
}

export async function sendItem(key) {
  return (await request(`/api/items/${key}/send`, { method: "POST" })).json();
}
