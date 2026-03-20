import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import ImageUpload from "../components/ImageUpload";
import { createItem } from "../api";

export default function RegisterItem() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [duplicate, setDuplicate] = useState(null);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      if (!name.trim() || !file) return;

      setLoading(true);
      setError(null);
      setDuplicate(null);

      try {
        const res = await createItem(name.trim(), description.trim() || null, file);
        navigate(`/items/${res.item.id}`);
      } catch (err) {
        if (err.duplicate) {
          setDuplicate(err.duplicate);
        } else {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    },
    [name, description, file, navigate]
  );

  return (
    <div className="max-w-xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Register Item
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Add a new product to the catalog with a reference image.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400"
            placeholder="Product name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 resize-none"
            placeholder="Optional description"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Reference Image *
          </label>
          <ImageUpload onFile={setFile} label="Upload a clear product photo" />
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-xl p-4 text-sm">
            {error}
          </div>
        )}

        {duplicate && (
          <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 rounded-xl p-4 text-sm space-y-2">
            <p>
              This item looks like a duplicate of{" "}
              <strong>{duplicate.existing_item_name}</strong> (
              {Math.round(duplicate.similarity * 100)}% match).
            </p>
            <Link
              to={`/items/${duplicate.existing_item_id}`}
              className="inline-block text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              View existing item
            </Link>
          </div>
        )}

        <button
          type="submit"
          disabled={!name.trim() || !file || loading}
          className="w-full px-6 py-3 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Registering...
            </span>
          ) : (
            "Register Item"
          )}
        </button>
      </form>
    </div>
  );
}
