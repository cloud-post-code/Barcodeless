const BASE = "";

/** Normalize FastAPI `detail` (string | object | validation array) into a message. */
export function formatFastApiDetail(detail) {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        if (e && typeof e === "object" && e.msg != null) {
          const loc = Array.isArray(e.loc) ? e.loc.join(".") : "";
          return loc ? `${loc}: ${e.msg}` : String(e.msg);
        }
        return typeof e === "string" ? e : JSON.stringify(e);
      })
      .join("; ");
  }
  if (typeof detail === "object") {
    if (detail.message != null) return String(detail.message);
    return JSON.stringify(detail);
  }
  return String(detail);
}

/** Read error message from a failed fetch Response (JSON or HTML/plain). */
export async function parseResponseError(res) {
  const text = await res.text();
  if (!text) return `HTTP ${res.status} ${res.statusText || ""}`.trim();
  try {
    const data = JSON.parse(text);
    if (data.detail !== undefined) {
      const msg = formatFastApiDetail(data.detail);
      if (msg) return msg;
    }
    return JSON.stringify(data);
  } catch {
    const snippet = text.replace(/\s+/g, " ").slice(0, 240);
    return snippet || `HTTP ${res.status}`;
  }
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(await parseResponseError(res));
  return res.json();
}

export async function listItems(skip = 0, limit = 50) {
  const res = await fetch(`${BASE}/items?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error(await parseResponseError(res));
  return res.json();
}

export async function getItem(itemId) {
  const res = await fetch(`${BASE}/items/${itemId}`);
  if (!res.ok) throw new Error(await parseResponseError(res));
  return res.json();
}

export async function createItem(name, description, imageFile) {
  const form = new FormData();
  form.append("name", name);
  if (description) form.append("description", description);
  form.append("image", imageFile, imageFile.name || "image.jpg");

  const res = await fetch(`${BASE}/items`, { method: "POST", body: form });

  if (res.status === 409) {
    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error("Duplicate item detected");
    }
    const err = new Error("Duplicate item detected");
    err.duplicate = data.detail;
    throw err;
  }

  if (!res.ok) {
    throw new Error(await parseResponseError(res));
  }

  return res.json();
}

export async function deleteItem(itemId) {
  const res = await fetch(`${BASE}/items/${itemId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await parseResponseError(res));
}

export async function addImage(itemId, imageFile) {
  const form = new FormData();
  form.append("image", imageFile, imageFile.name || "image.jpg");

  const res = await fetch(`${BASE}/items/${itemId}/images`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error(await parseResponseError(res));
  return res.json();
}

export async function scanImage(imageFile, topK = 5) {
  const form = new FormData();
  form.append("image", imageFile, imageFile.name || "image.jpg");

  const res = await fetch(`${BASE}/scan?top_k=${topK}`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error(await parseResponseError(res));
  return res.json();
}

export function imageUrl(itemId, imageId) {
  return `${BASE}/items/${itemId}/images/${imageId}`;
}
