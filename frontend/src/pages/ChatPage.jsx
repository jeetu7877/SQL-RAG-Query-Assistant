import { useCallback, useEffect, useMemo, useState } from "react";
import ChatWindow from "../components/ChatWindow";
import Sidebar from "../components/Sidebar";
import { useConnection } from "../context/ConnectionContext";
import { askQuestion, cancelWrite, confirmWrite, getServerInfo, previewWrite } from "../services/chatService";
import { fetchSchema } from "../services/databaseService";

let nextId = 1;

export default function ChatPage() {
  const { connection } = useConnection();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState(null);
  const [writesEnabled, setWritesEnabled] = useState(false);
  const [writeMode, setWriteMode] = useState(false); // always starts OFF

  useEffect(() => {
    fetchSchema().then(setSchema).catch(() => setSchema(null));
    getServerInfo().then((i) => setWritesEnabled(!!i.writes_enabled)).catch(() => setWritesEnabled(false));
  }, []);

  const suggestions = useMemo(() => {
    const names = (schema?.tables ?? []).slice(0, 3).map((t) => t.name.replace(/_/g, " "));
    return [
      ...names.map((n) => `How many rows are in ${n}?`),
      ...(names[0] ? [`Show 5 sample records from ${names[0]}`] : []),
    ];
  }, [schema]);

  const history = useMemo(
    () => [...new Set(messages.filter((m) => m.role === "user").map((m) => m.text))].reverse().slice(0, 12),
    [messages]
  );

  const patch = (id, changes) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...changes } : m)));

  const send = useCallback(
    async (question) => {
      if (loading) return;
      setMessages((m) => [...m, { id: nextId++, role: "user", text: question }]);
      setLoading(true);
      try {
        if (writeMode) {
          const data = await previewWrite(question);
          setMessages((m) => [...m, { id: nextId++, role: "assistant", kind: "write", data, status: "pending" }]);
        } else {
          const data = await askQuestion(question);
          setMessages((m) => [...m, { id: nextId++, role: "assistant", data }]);
        }
      } catch (err) {
        setMessages((m) => [...m, { id: nextId++, role: "assistant", error: true, text: err.message }]);
      } finally {
        setLoading(false);
      }
    },
    [loading, writeMode]
  );

  const onConfirmWrite = useCallback(
    async (id) => {
      const msg = messages.find((m) => m.id === id);
      if (!msg || msg.status !== "pending") return;
      patch(id, { status: "running" });
      try {
        const result = await confirmWrite(msg.data.token);
        patch(id, { status: "done", result });
        setWriteMode(false); // back to read-only after every successful write
        fetchSchema(true).then(setSchema).catch(() => {});
      } catch (err) {
        patch(id, { status: "failed", error: err.message });
      }
    },
    [messages]
  );

  const onCancelWrite = useCallback(
    async (id) => {
      const msg = messages.find((m) => m.id === id);
      if (!msg || msg.status !== "pending") return;
      patch(id, { status: "cancelled" });
      cancelWrite(msg.data.token).catch(() => {});
    },
    [messages]
  );

  return (
    <div className="flex min-h-0 flex-1">
      <Sidebar tableCount={schema?.table_count} history={history} onPick={send} disabled={loading} />
      <ChatWindow
        messages={messages}
        loading={loading}
        onSend={send}
        suggestions={writeMode ? [] : suggestions}
        dbName={connection.database_name}
        writesEnabled={writesEnabled}
        writeMode={writeMode}
        onToggleWrite={() => setWriteMode((v) => !v)}
        onConfirmWrite={onConfirmWrite}
        onCancelWrite={onCancelWrite}
      />
    </div>
  );
}
