import { useEffect, useRef, useState } from "react";
import { Loader2, SendHorizontal, Sparkles } from "lucide-react";
import ChatMessage from "./ChatMessage";

export default function ChatWindow({ messages, loading, onSend, suggestions, dbName }) {
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const submit = (e) => {
    e?.preventDefault();
    const q = draft.trim();
    if (!q || loading) return;
    onSend(q);
    setDraft("");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) submit(e);
  };

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {messages.length === 0 && (
            <div className="py-10">
              <h2 className="text-2xl font-semibold tracking-tight">Connected to {dbName}</h2>
              <p className="mt-2 max-w-lg text-[15px] leading-relaxed text-mute">
                Ask a question about your data in plain English. The assistant writes the SQL, runs it read-only,
                and shows you both the query and the result.
              </p>
              {suggestions.length > 0 && (
                <div className="mt-6 flex flex-wrap gap-2">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => onSend(s)}
                      className="inline-flex items-center gap-2 rounded-full border border-line px-3.5 py-1.5 text-sm text-mute transition-colors hover:border-accent/60 hover:text-ink"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-accent" aria-hidden /> {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((m) => (
            <ChatMessage key={m.id} message={m} />
          ))}

          {loading && (
            <div className="flex items-center gap-3 text-sm text-mute" role="status">
              <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
              Generating SQL and running the query...
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <form onSubmit={submit} className="border-t border-line bg-panel px-4 py-3">
        <div className="mx-auto flex max-w-4xl items-end gap-3">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            maxLength={1000}
            placeholder="Ask a question about your database..."
            aria-label="Your question"
            className="max-h-40 min-h-[46px] flex-1 resize-none rounded-xl border border-line bg-base px-4 py-3 text-[15px] placeholder:text-mute/60 focus:border-accent focus:outline-none"
          />
          <button type="submit" disabled={!draft.trim() || loading} className="btn-primary h-[46px] !px-4" aria-label="Send question">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
            <span className="hidden sm:inline">Send</span>
          </button>
        </div>
      </form>
    </div>
  );
}
