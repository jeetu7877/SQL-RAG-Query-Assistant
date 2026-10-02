import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, ArrowRight, ChevronsDownUp, ChevronsUpDown, DatabaseZap, Download, FileSpreadsheet, RefreshCw, Search } from "lucide-react";
import LoadingSpinner from "../components/LoadingSpinner";
import SchemaTableCard from "../components/SchemaTableCard";
import { downloadDatabaseExport, fetchSchema } from "../services/databaseService";

function Stat({ label, value }) {
  return (
    <div className="card px-4 py-3">
      <p className="text-xs text-mute">{label}</p>
      <p className="mt-1 truncate text-xl font-semibold">{value}</p>
    </div>
  );
}

export default function SchemaPage() {
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(() => new Set());
  const [exporting, setExporting] = useState("");

  const load = useCallback(async (refresh = false) => {
    setLoading(true);
    setError("");
    try {
      setSchema(await fetchSchema(refresh));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tables = useMemo(() => {
    const q = query.trim().toLowerCase();
    const all = schema?.tables ?? [];
    return q ? all.filter((t) => t.name.toLowerCase().includes(q) || t.columns.some((c) => c.name.toLowerCase().includes(q))) : all;
  }, [schema, query]);

  const download = async (format) => {
    setExporting(format);
    setError("");
    try {
      await downloadDatabaseExport(format);
    } catch (err) {
      setError(err.message || "Export failed.");
    } finally {
      setExporting("");
    }
  };

  const toggle = (name) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });

  return (
    <main className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Database schema</h1>
            <p className="mt-1 text-sm text-mute">Download the connected database as Excel or a ZIP of CSV files.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => download("csv")} disabled={!!exporting || loading} className="btn-ghost">
              <Download className="h-4 w-4" aria-hidden />
              {exporting === "csv" ? "Exporting..." : "CSV"}
            </button>
            <button onClick={() => download("xlsx")} disabled={!!exporting || loading} className="btn-primary">
              <FileSpreadsheet className="h-4 w-4" aria-hidden />
              {exporting === "xlsx" ? "Exporting..." : "Excel"}
            </button>
            <button onClick={() => load(true)} disabled={loading || !!exporting} className="btn-ghost">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden /> Refresh
            </button>
          </div>
        </div>

        {loading && !schema && <LoadingSpinner label="Reading schema from PostgreSQL..." className="py-20" />}

        {error && (
          <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center">
            <AlertCircle className="h-8 w-8 text-red-300" aria-hidden />
            <p className="max-w-md text-sm text-red-200">{error}</p>
            <button onClick={() => load(true)} className="btn-ghost">
              Try again
            </button>
          </div>
        )}

        {schema && !error && (
          <>
            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-5">
              <Stat label="Database" value={schema.database_name} />
              <Stat label="Host" value={schema.host} />
              <Stat label="Tables" value={schema.table_count} />
              <Stat label="Columns" value={schema.column_count} />
              <Stat label="Relationships" value={schema.relationship_count} />
            </div>

            {schema.tables.length === 0 ? (
              <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
                <DatabaseZap className="h-8 w-8 text-mute" aria-hidden />
                <p className="font-medium">No tables found</p>
                <p className="max-w-sm text-sm text-mute">
                  This database has no tables in the public schema, or the connected user cannot see them.
                </p>
              </div>
            ) : (
              <>
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <div className="relative min-w-[220px] flex-1">
                    <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search tables or columns"
                      aria-label="Search tables"
                      className="w-full rounded-xl border border-line bg-panel py-2.5 pl-10 pr-4 text-sm placeholder:text-mute/60 focus:border-accent focus:outline-none"
                    />
                  </div>
                  <button onClick={() => setOpen(new Set(tables.map((t) => t.name)))} className="btn-ghost">
                    <ChevronsUpDown className="h-4 w-4" aria-hidden /> Expand all
                  </button>
                  <button onClick={() => setOpen(new Set())} className="btn-ghost">
                    <ChevronsDownUp className="h-4 w-4" aria-hidden /> Collapse all
                  </button>
                </div>

                {tables.length === 0 ? (
                  <p className="card px-6 py-10 text-center text-sm text-mute">
                    No tables or columns match “{query}”.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {tables.map((t) => (
                      <SchemaTableCard key={t.name} table={t} expanded={open.has(t.name)} onToggle={() => toggle(t.name)} />
                    ))}
                  </div>
                )}

                <section className="mt-10">
                  <h2 className="mb-3 text-lg font-semibold">Relationships</h2>
                  {schema.relationships.length === 0 ? (
                    <p className="text-sm text-mute">No foreign key relationships were found.</p>
                  ) : (
                    <ul className="card divide-y divide-line">
                      {schema.relationships.map((r, i) => (
                        <li key={i} className="flex flex-wrap items-center gap-3 px-4 py-3 font-mono text-[13px]">
                          <span className="rounded-md bg-raised px-2 py-1">
                            {r.from_table}.<span className="text-accent-soft">{r.from_column}</span>
                          </span>
                          <ArrowRight className="h-4 w-4 text-mute" aria-hidden />
                          <span className="rounded-md bg-raised px-2 py-1">
                            {r.to_table}.<span className="text-sky-300">{r.to_column}</span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </>
            )}
          </>
        )}
      </div>
    </main>
  );
}
