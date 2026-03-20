import { Link } from "react-router-dom";

export default function ScanResultCard({ result, allItems }) {
  const item = allItems?.find((i) => i.id === result.item_id);
  const thumbSrc =
    item?.image_ids?.length > 0
      ? `/items/${item.id}/images/${item.image_ids[0]}`
      : null;

  const pct = Math.round(result.confidence * 100);

  const barColor =
    pct >= 80
      ? "bg-emerald-500"
      : pct >= 50
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <Link
      to={`/items/${result.item_id}`}
      className="flex items-center gap-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex-shrink-0 w-16 h-16 rounded-lg bg-gray-100 dark:bg-gray-800 overflow-hidden flex items-center justify-center">
        {thumbSrc ? (
          <img src={thumbSrc} alt={result.name} className="w-full h-full object-cover" />
        ) : (
          <span className="text-2xl text-gray-300 dark:text-gray-600">#{result.rank}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
            {result.name}
          </h3>
          <span className="text-sm font-mono font-bold ml-2 whitespace-nowrap">{pct}%</span>
        </div>
        {result.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
            {result.description}
          </p>
        )}
        <div className="mt-2 h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </Link>
  );
}
