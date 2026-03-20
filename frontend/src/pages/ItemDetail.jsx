import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import { getItem, deleteItem, addImage, imageUrl } from "../api";

export default function ItemDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileRef = useRef();

  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showDelete, setShowDelete] = useState(false);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItem(await getItem(id));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = useCallback(async () => {
    try {
      await deleteItem(id);
      navigate("/catalog");
    } catch (err) {
      setError(err.message);
    }
  }, [id, navigate]);

  const handleAddImage = useCallback(
    async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setUploading(true);
      try {
        setItem(await addImage(id, file));
      } catch (err) {
        setError(err.message);
      } finally {
        setUploading(false);
        if (fileRef.current) fileRef.current.value = "";
      }
    },
    [id]
  );

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <svg className="animate-spin h-8 w-8 text-indigo-600" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error && !item) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!item) return null;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {item.name}
          </h1>
          {item.description && (
            <p className="mt-1 text-gray-600 dark:text-gray-400">
              {item.description}
            </p>
          )}
          <p className="mt-2 text-xs text-gray-400">
            Created {new Date(item.created_at).toLocaleDateString()}
          </p>
        </div>
        <button
          onClick={() => setShowDelete(true)}
          className="flex-shrink-0 px-4 py-2 text-sm font-medium rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
        >
          Delete
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 rounded-xl p-4 text-sm">
          {error}
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Reference Images ({item.image_ids?.length || 0})
          </h2>
          <label
            className={`px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer ${
              uploading ? "opacity-50 pointer-events-none" : ""
            }`}
          >
            {uploading ? "Uploading..." : "Add Image"}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAddImage}
            />
          </label>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {item.image_ids?.map((imgId) => (
            <div
              key={imgId}
              className="aspect-square bg-gray-100 dark:bg-gray-800 rounded-xl overflow-hidden"
            >
              <img
                src={imageUrl(item.id, imgId)}
                alt={item.name}
                className="w-full h-full object-cover"
              />
            </div>
          ))}
        </div>
      </div>

      {item.metadata && Object.keys(item.metadata).length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Metadata
          </h2>
          <pre className="bg-gray-100 dark:bg-gray-800 rounded-xl p-4 text-sm overflow-x-auto">
            {JSON.stringify(item.metadata, null, 2)}
          </pre>
        </div>
      )}

      <ConfirmDialog
        open={showDelete}
        title="Delete Item"
        message={`Are you sure you want to delete "${item.name}"? This action cannot be undone.`}
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
      />
    </div>
  );
}
