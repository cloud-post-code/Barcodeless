import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Scanner from "./pages/Scanner";
import Catalog from "./pages/Catalog";
import RegisterItem from "./pages/RegisterItem";
import BulkRegister from "./pages/BulkRegister";
import ItemDetail from "./pages/ItemDetail";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Scanner />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/register" element={<RegisterItem />} />
        <Route path="/register/bulk" element={<BulkRegister />} />
        <Route path="/items/:id" element={<ItemDetail />} />
      </Route>
    </Routes>
  );
}
