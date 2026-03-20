const BASE = "";

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function listItems(skip = 0, limit = 50) {
  const res = await fetch(`${BASE}/items?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export async function getItem(itemId) {
  const res = await fetch(`${BASE}/items/${itemId}`);
  if (!res.ok) throw new Error("Failed to fetch item");
  return res.json();
}

export async function createItem(name, description, imageFile) {
  const form = new FormData();
  form.append("name", name);
  if (description) form.append("description", description);
  form.append("image", imageFile);

  const res = await fetch(`${BASE}/items`, { method: "POST", body: form });

  if (res.status === 409) {
    const data = await res.json();
    const err = new Error("Duplicate item detected");
    err.duplicate = data.detail;
    throw err;
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to create item");
  }

  return res.json();
}

export async function deleteItem(itemId) {
  const res = await fetch(`${BASE}/items/${itemId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete item");
}

export async function addImage(itemId, imageFile) {
  const form = new FormData();
  form.append("image", imageFile);

  const res = await fetch(`${BASE}/items/${itemId}/images`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error("Failed to add image");
  return res.json();
}

export async function scanImage(imageFile, topK = 5) {
  const form = new FormData();
  form.append("image", imageFile);

  const res = await fetch(`${BASE}/scan?top_k=${topK}`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) throw new Error("Scan failed");
  return res.json();
}

export function imageUrl(itemId, imageId) {
  return `${BASE}/items/${itemId}/images/${imageId}`;
}
