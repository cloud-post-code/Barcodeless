import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Scanner from "./pages/Scanner";
import Catalog from "./pages/Catalog";
import BulkRegister from "./pages/BulkRegister";
import ItemDetail from "./pages/ItemDetail";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Scanner />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/register" element={<BulkRegister />} />
        <Route path="/register/bulk" element={<Navigate to="/register" replace />} />
        <Route path="/items/:id" element={<ItemDetail />} />
      </Route>
    </Routes>
  );
}
