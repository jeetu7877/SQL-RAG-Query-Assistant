import { useState } from "react";
import { AlertCircle, CheckCircle2, Database, Eye, EyeOff, Loader2, ShieldCheck } from "lucide-react";
import { useConnection } from "../context/ConnectionContext";

export default function DatabaseConnect() {
  const { connect, activate } = useConnection();
  const [url, setUrl] = useState("");
  const [reveal, setReveal] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | connecting | success | error
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!url.trim() || status === "connecting") return;
    setStatus("connecting");
    setError("");
    try {
      const info = await connect(url.trim());
      setUrl(""); // never keep the password in the page after connecting
      setStatus("success");
      setTimeout(() => activate(info), 900);
    } catch (err) {
      setStatus("error");
      setError(err.message);
    }
  };

  const busy = status === "connecting" || status === "success";

  return (
    <main className="flex min-h-full items-center justify-center px-4 py-10">
      <div className="w-full max-w-xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-base">
            <Database className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">PostgreSQL Text-to-SQL AI Assistant</h1>
        </div>

        <p className="mb-6 max-w-md text-[15px] leading-relaxed text-mute">
          Connect your PostgreSQL database to start querying it using natural language.
        </p>

        <form onSubmit={submit} className="card p-6">
          <label htmlFor="db-url" className="mb-2 block text-sm font-medium">
            PostgreSQL connection URL
          </label>
          <div className="relative">
            <input
              id="db-url"
              type={reveal ? "text" : "password"}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="postgresql://username:password@host:5432/database"
              autoComplete="off"
              spellCheck={false}
              disabled={busy}
              className="w-full rounded-xl border border-line bg-base py-3 pl-4 pr-11 font-mono text-sm placeholder:text-mute/60 focus:border-accent focus:outline-none disabled:opacity-60"
            />
            <button
              type="button"
              onClick={() => setReveal((r) => !r)}
              aria-label={reveal ? "Hide connection URL" : "Show connection URL"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-mute hover:text-ink"
            >
              {reveal ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          <div aria-live="polite">
            {status === "error" && (
              <p className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
              </p>
            )}
            {status === "success" && (
              <p className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
                <CheckCircle2 className="h-4 w-4" /> PostgreSQL connected successfully.
              </p>
            )}
          </div>

          <button type="submit" disabled={!url.trim() || busy} className="btn-primary mt-5 w-full">
            {status === "connecting" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Connecting to PostgreSQL...
              </>
            ) : (
              "Connect database"
            )}
          </button>
        </form>

        <p className="mt-5 flex items-start gap-2 text-[13px] leading-relaxed text-mute">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
          <span>
            Your URL stays on the server and is never sent to the AI. Only table structure is shared with
            Gemini, and only read-only queries run. For extra safety, connect with a read-only database user.
          </span>
        </p>
      </div>
    </main>
  );
}
