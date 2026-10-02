import { ChevronDown, Key, Link2, Table2 } from "lucide-react";

export default function SchemaTableCard({ table, expanded, onToggle }) {
  const id = `table-${table.name}`;
  return (
    <article className="card overflow-hidden">
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={id}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left hover:bg-raised/40"
      >
        <Table2 className="h-5 w-5 shrink-0 text-accent" aria-hidden />
        <span className="font-mono text-[15px] font-medium">{table.name}</span>
        <span className="text-xs text-mute">
          {table.columns.length} columns
          {table.row_estimate != null && table.row_estimate > 0 && ` · ~${table.row_estimate.toLocaleString()} rows`}
        </span>
        <ChevronDown
          className={`ml-auto h-4 w-4 shrink-0 text-mute transition-transform ${expanded ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>

      {expanded && (
        <div id={id} className="border-t border-line">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-mute">
                  <th className="px-4 py-2 font-medium">Column</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Nullable</th>
                  <th className="px-4 py-2 font-medium">Default</th>
                  <th className="px-4 py-2 font-medium">Keys</th>
                </tr>
              </thead>
              <tbody>
                {table.columns.map((c) => (
                  <tr key={c.name} className="border-t border-line/60">
                    <td className="whitespace-nowrap px-4 py-2 font-mono text-[13px]">{c.name}</td>
                    <td className="whitespace-nowrap px-4 py-2 font-mono text-[13px] text-sky-300">{c.type}</td>
                    <td className="px-4 py-2 text-mute">{c.nullable ? "Yes" : "No"}</td>
                    <td className="max-w-[220px] truncate px-4 py-2 font-mono text-xs text-mute" title={c.default ?? ""}>
                      {c.default ?? "-"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2">
                      <span className="flex gap-1.5">
                        {c.primary_key && (
                          <span className="badge bg-accent/15 text-accent-soft">
                            <Key className="h-3 w-3" aria-hidden /> PK
                          </span>
                        )}
                        {c.foreign_key && (
                          <span className="badge bg-sky-400/15 text-sky-300">
                            <Link2 className="h-3 w-3" aria-hidden /> FK
                          </span>
                        )}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(table.foreign_keys.length > 0 || table.indexes.length > 0) && (
            <div className="space-y-2 border-t border-line px-4 py-3 text-xs text-mute">
              {table.foreign_keys.map((fk, i) => (
                <p key={i}>
                  <span className="text-ink">References</span>{" "}
                  <span className="font-mono">
                    {fk.columns.join(", ")} → {fk.referred_table}({fk.referred_columns.join(", ")})
                  </span>
                </p>
              ))}
              {table.indexes.map((ix) => (
                <p key={ix.name}>
                  <span className="text-ink">{ix.unique ? "Unique index" : "Index"}</span>{" "}
                  <span className="font-mono">
                    {ix.name} ({ix.columns.join(", ")})
                  </span>
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
