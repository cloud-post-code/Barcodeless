import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchHealth } from "../api";

const linkClass = ({ isActive }) =>
  `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
    isActive
      ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800"
  }`;

export default function Navbar() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const check = () => fetchHealth().then(setHealth).catch(() => setHealth(null));
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  const statusColor = !health
    ? "bg-red-500"
    : health.model_loaded
      ? "bg-emerald-500"
      : "bg-amber-500";

  const statusLabel = !health
    ? "Offline"
    : health.model_loaded
      ? "Ready"
      : "Loading model...";

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-1">
            <NavLink to="/" className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mr-6">
              Barcodeless
            </NavLink>
            <NavLink to="/" className={linkClass} end>
              Scan
            </NavLink>
            <NavLink to="/catalog" className={linkClass}>
              Catalog
            </NavLink>
            <NavLink to="/register" className={linkClass}>
              Register
            </NavLink>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <span className={`inline-block w-2 h-2 rounded-full ${statusColor}`} />
            {statusLabel}
          </div>
        </div>
      </div>
    </nav>
  );
}
