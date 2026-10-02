import { Link } from "react-router-dom";
import { History, Network, Server } from "lucide-react";
import { useConnection } from "../context/ConnectionContext";

export default function Sidebar({ tableCount, history, onPick, disabled }) {
  const { connection } = useConnection();

  return (
    <aside className="hidden w-72 shrink-0 flex-col gap-5 overflow-y-auto border-r border-line bg-panel p-4 lg:flex">
      <section>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Server className="h-4 w-4 text-accent" aria-hidden /> Database
        </h2>
        <dl className="space-y-2.5 rounded-xl border border-line bg-base p-3 text-sm">
          <div>
            <dt className="text-xs text-mute">Name</dt>
            <dd className="truncate font-medium">{connection.database_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-mute">Host</dt>
            <dd className="truncate font-mono text-[13px]">{connection.host}</dd>
          </div>
          <div>
            <dt className="text-xs text-mute">Status</dt>
            <dd className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden /> Connected
            </dd>
          </div>
          {tableCount != null && (
            <div>
              <dt className="text-xs text-mute">Tables</dt>
              <dd>{tableCount}</dd>
            </div>
          )}
        </dl>
        <Link to="/schema" className="btn-ghost mt-3 w-full">
          <Network className="h-4 w-4" aria-hidden /> Open schema
        </Link>
      </section>

      <section className="min-h-0 flex-1">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <History className="h-4 w-4 text-accent" aria-hidden /> Recent questions
        </h2>
        {history.length === 0 ? (
          <p className="text-sm text-mute">Questions you ask will appear here.</p>
        ) : (
          <ul className="space-y-1">
            {history.map((q, i) => (
              <li key={`${i}-${q}`}>
                <button
                  onClick={() => onPick(q)}
                  disabled={disabled}
                  title={q}
                  className="w-full truncate rounded-lg px-2.5 py-2 text-left text-sm text-mute transition-colors hover:bg-raised hover:text-ink disabled:opacity-50"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
