import { Clock, Rows3 } from "lucide-react";

const isNum = (v) => typeof v === "number";

function Cell({ value }) {
  if (value === null || value === undefined) return <span className="italic text-mute/70">null</span>;
  if (typeof value === "boolean") return <span>{String(value)}</span>;
  if (isNum(value)) return <>{value.toLocaleString(undefined, { maximumFractionDigits: 4 })}</>;
  return <>{String(value)}</>;
}

export default function ResultTable({ columns, rows, rowCount, executionTimeMs, truncated }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-base">
      <div className="max-h-96 overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-raised">
            <tr>
              {columns.map((c) => (
                <th key={c} scope="col" className="whitespace-nowrap border-b border-line px-3.5 py-2.5 text-left font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length || 1} className="px-3.5 py-6 text-center text-mute">
                  No rows returned.
                </td>
              </tr>
            ) : (
              rows.map((row, r) => (
                <tr key={r} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                  {row.map((v, c) => (
                    <td
                      key={c}
                      className={`max-w-xs truncate px-3.5 py-2 ${isNum(v) ? "text-right font-mono text-[13px] tabular-nums" : ""}`}
                      title={typeof v === "string" ? v : undefined}
                    >
                      <Cell value={v} />
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-3.5 py-2 text-xs text-mute">
        <span className="inline-flex items-center gap-1.5">
          <Rows3 className="h-3.5 w-3.5" aria-hidden /> {rowCount} {rowCount === 1 ? "row" : "rows"}
        </span>
        <span>{columns.length} {columns.length === 1 ? "column" : "columns"}</span>
        <span className="inline-flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" aria-hidden /> {executionTimeMs} ms
        </span>
        {truncated && <span className="text-accent-soft">Showing the first {rowCount} rows only</span>}
      </div>
    </div>
  );
}
