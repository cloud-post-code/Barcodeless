import { useCallback, useEffect, useId, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { createItem } from "../api";

const IMAGE_EXT = /\.(jpe?g|png|gif|webp|bmp|tiff?|heic|heif)$/i;

function isLikelyImageFile(file) {
  if (file.type && file.type.startsWith("image/")) return true;
  return IMAGE_EXT.test(file.name);
}

function basenameNoExt(filename) {
  const base = filename.replace(/^.*[/\\]/, "");
  return base.replace(/\.[^.]+$/, "") || base || "Untitled";
}

function makeRow(file) {
  return {
    key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2)}`,
    file,
    name: basenameNoExt(file.name),
    description: "",
  };
}

export default function BulkRegister() {
  const inputId = useId();
  const [rows, setRows] = useState([]);
  const [globalDescription, setGlobalDescription] = useState("");
  const [processing, setProcessing] = useState(false);
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);
  const [rowStatus, setRowStatus] = useState({}); // key -> 'pending' | 'running' | 'ok' | 'dup' | 'err'
  const [rowErrors, setRowErrors] = useState({}); // key -> error message

  const totalRows = rows.length;
  const canStart = totalRows > 0 && !processing;

  const addFiles = useCallback((fileList) => {
    const files = Array.from(fileList || []).filter(isLikelyImageFile);
    if (files.length === 0) return;
    setRows((prev) => [...prev, ...files.map(makeRow)]);
  }, []);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const updateRow = useCallback((key, patch) => {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }, []);

  const removeRow = useCallback((key) => {
    setRows((prev) => prev.filter((r) => r.key !== key));
  }, []);

  const clearAll = useCallback(() => {
    setRows([]);
    setRowStatus({});
    setRowErrors({});
    setCompleted(0);
    setTotal(0);
  }, []);

  const runBulk = useCallback(async () => {
    if (rows.length === 0) return;
    setProcessing(true);
    setCompleted(0);
    setTotal(rows.length);
    const status = {};
    rows.forEach((r) => {
      status[r.key] = "pending";
    });
    setRowStatus(status);
    setRowErrors({});

    let done = 0;
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      setRowStatus((s) => ({ ...s, [row.key]: "running" }));

      const desc =
        row.description.trim() ||
        (globalDescription.trim() || null);

      try {
        await createItem(row.name.trim() || basenameNoExt(row.file.name), desc, row.file);
        setRowStatus((s) => ({ ...s, [row.key]: "ok" }));
      } catch (err) {
        if (err.duplicate) {
          setRowStatus((s) => ({ ...s, [row.key]: "dup" }));
        } else {
          const msg = err.message || "Failed";
          setRowStatus((s) => ({ ...s, [row.key]: "err" }));
          setRowErrors((e) => ({ ...e, [row.key]: msg }));
        }
      }

      done += 1;
      setCompleted(done);
    }

    setProcessing(false);
  }, [rows, globalDescription]);

  const summary = useMemo(() => {
    const keys = rows.map((r) => r.key);
    let ok = 0;
    let dup = 0;
    let err = 0;
    keys.forEach((k) => {
      const s = rowStatus[k];
      if (s === "ok") ok += 1;
      else if (s === "dup") dup += 1;
      else if (s === "err") err += 1;
    });
    return { ok, dup, err };
  }, [rows, rowStatus]);

  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Register items
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Add one or many images. Each image becomes one catalog item. Names default to the
          file name — edit before starting. Items are sent one at a time so the server can
          process embeddings safely.
        </p>
        <p className="mt-2 text-sm">
          <Link
            to="/catalog"
            className="text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            View catalog
          </Link>
        </p>
      </div>

      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 text-center bg-gray-50/50 dark:bg-gray-900/30"
      >
        <label
          htmlFor={inputId}
          className="cursor-pointer text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          Choose images
        </label>
        <span className="text-gray-500 dark:text-gray-400 text-sm"> or drag and drop here</span>
        <input
          id={inputId}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <p className="mt-2 text-xs text-gray-400">PNG, JPEG, WebP, etc.</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Default description (optional)
        </label>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Applied to any row that has an empty description.
        </p>
        <textarea
          value={globalDescription}
          onChange={(e) => setGlobalDescription(e.target.value)}
          rows={2}
          disabled={processing}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none disabled:opacity-60"
          placeholder="Optional — applies to all rows without their own description"
        />
      </div>

      {totalRows > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Queue ({totalRows})
            </h2>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={clearAll}
                disabled={processing}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
              >
                Clear queue
              </button>
              <button
                type="button"
                onClick={runBulk}
                disabled={!canStart}
                className="px-4 py-1.5 text-sm font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? "Processing…" : "Register all"}
              </button>
            </div>
          </div>

          {processing && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                <span>Progress</span>
                <span>
                  {completed} / {total} completed ({pct}%)
                </span>
              </div>
              <div className="h-3 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-600 transition-[width] duration-300 ease-out rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )}

          {!processing && completed > 0 && total > 0 && (
            <div className="text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                {summary.ok} registered
              </span>
              {summary.dup > 0 && (
                <span className="text-amber-600 dark:text-amber-400 ml-3">
                  {summary.dup} duplicate{summary.dup !== 1 ? "s" : ""}
                </span>
              )}
              {summary.err > 0 && (
                <span className="text-red-600 dark:text-red-400 ml-3">
                  {summary.err} failed
                </span>
              )}
            </div>
          )}

          <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden max-h-[min(60vh,28rem)] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-900/80 sticky top-0 z-10">
                <tr className="text-left text-gray-600 dark:text-gray-400">
                  <th className="px-3 py-2 font-medium w-10">#</th>
                  <th className="px-3 py-2 font-medium">Preview</th>
                  <th className="px-3 py-2 font-medium min-w-[8rem]">Name</th>
                  <th className="px-3 py-2 font-medium min-w-[6rem] hidden sm:table-cell">
                    Description
                  </th>
                  <th className="px-3 py-2 font-medium w-24">Status</th>
                  <th className="px-3 py-2 w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {rows.map((row, i) => {
                  const s = rowStatus[row.key];
                  return (
                    <tr key={row.key} className="bg-white dark:bg-gray-950/40">
                      <td className="px-3 py-2 text-gray-400 tabular-nums">{i + 1}</td>
                      <td className="px-3 py-2">
                        <FileThumb file={row.file} />
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="text"
                          value={row.name}
                          onChange={(e) => updateRow(row.key, { name: e.target.value })}
                          disabled={processing}
                          className="w-full min-w-0 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-sm disabled:opacity-60"
                        />
                      </td>
                      <td className="px-3 py-2 hidden sm:table-cell">
                        <input
                          type="text"
                          value={row.description}
                          onChange={(e) =>
                            updateRow(row.key, { description: e.target.value })
                          }
                          disabled={processing}
                          placeholder="Optional"
                          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-sm disabled:opacity-60"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge status={s} error={rowErrors[row.key]} />
                      </td>
                      <td className="px-3 py-2">
                        <button
                          type="button"
                          onClick={() => removeRow(row.key)}
                          disabled={processing}
                          className="text-red-600 dark:text-red-400 text-xs hover:underline disabled:opacity-40"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function FileThumb({ file }) {
  const [url, setUrl] = useState("");

  useEffect(() => {
    const u = URL.createObjectURL(file);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);

  if (!url) {
    return (
      <div className="h-12 w-12 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
    );
  }

  return (
    <img
      src={url}
      alt=""
      className="h-12 w-12 object-cover rounded-lg border border-gray-200 dark:border-gray-700"
    />
  );
}

function StatusBadge({ status, error }) {
  if (!status || status === "pending") {
    return <span className="text-gray-400 text-xs">—</span>;
  }
  if (status === "running") {
    return (
      <span className="inline-flex items-center gap-1 text-indigo-600 dark:text-indigo-400 text-xs">
        <span className="inline-block h-3 w-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
        Working
      </span>
    );
  }
  if (status === "ok") {
    return <span className="text-emerald-600 dark:text-emerald-400 text-xs font-medium">Done</span>;
  }
  if (status === "dup") {
    return <span className="text-amber-600 dark:text-amber-400 text-xs">Duplicate</span>;
  }
  if (status === "err") {
    return (
      <span
        className="text-red-600 dark:text-red-400 text-xs block max-w-[10rem] truncate"
        title={error || undefined}
      >
        {error || "Error"}
      </span>
    );
  }
  return null;
}
