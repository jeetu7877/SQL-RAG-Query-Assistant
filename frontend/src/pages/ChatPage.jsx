import { useCallback, useEffect, useMemo, useState } from "react";
import ChatWindow from "../components/ChatWindow";
import Sidebar from "../components/Sidebar";
import { useConnection } from "../context/ConnectionContext";
import { askQuestion } from "../services/chatService";
import { fetchSchema } from "../services/databaseService";

let nextId = 1;

export default function ChatPage() {
  const { connection } = useConnection();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [schema, setSchema] = useState(null);

  // schema is used only for the sidebar table count and dynamic example questions
  useEffect(() => {
    fetchSchema()
      .then(setSchema)
      .catch(() => setSchema(null));
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

  const send = useCallback(
    async (question) => {
      if (loading) return;
      setMessages((m) => [...m, { id: nextId++, role: "user", text: question }]);
      setLoading(true);
      try {
        const data = await askQuestion(question);
        setMessages((m) => [...m, { id: nextId++, role: "assistant", data }]);
      } catch (err) {
        setMessages((m) => [...m, { id: nextId++, role: "assistant", error: true, text: err.message }]);
      } finally {
        setLoading(false);
      }
    },
    [loading]
  );

  return (
    <div className="flex min-h-0 flex-1">
      <Sidebar tableCount={schema?.table_count} history={history} onPick={send} disabled={loading} />
      <ChatWindow
        messages={messages}
        loading={loading}
        onSend={send}
        suggestions={suggestions}
        dbName={connection.database_name}
      />
    </div>
  );
}
