import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import DatabaseConnect from "./components/DatabaseConnect";
import ChatPage from "./pages/ChatPage";
import SchemaPage from "./pages/SchemaPage";
import { useConnection } from "./context/ConnectionContext";

export default function App() {
  const { connection } = useConnection();

  if (!connection) return <DatabaseConnect />;

  return (
    <div className="flex h-full flex-col">
      <Navbar />
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/schema" element={<SchemaPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
