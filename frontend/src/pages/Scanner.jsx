import { useState, useCallback } from "react";
import ImageUpload from "../components/ImageUpload";
import ScanResultCard from "../components/ScanResultCard";
import { scanImage, listItems } from "../api";

export default function Scanner() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scanTime, setScanTime] = useState(null);

  const handleScan = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const [scanRes, itemList] = await Promise.all([
        scanImage(file),
        listItems(0, 200),
      ]);
      setResults(scanRes.results);
      setItems(itemList);
      setScanTime(scanRes.scan_time_ms);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [file]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Scan & Identify
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload a product photo to identify it against your catalog.
        </p>
      </div>

      <ImageUpload onFile={setFile} label="Drop a product photo here" />

      <button
        onClick={handleScan}
        disabled={!file || loading}
        className="w-full sm:w-auto px-6 py-3 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Scanning...
          </span>
        ) : (
          "Scan Image"
        )}
      </button>

      {error && (
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Results
            </h2>
            {scanTime != null && (
              <span className="text-xs text-gray-400">
                {scanTime.toFixed(0)} ms
              </span>
            )}
          </div>
          {results.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No matches found. Try registering items first.
            </p>
          ) : (
            <div className="space-y-3">
              {results.map((r) => (
                <ScanResultCard key={r.item_id} result={r} allItems={items} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
