import { AlertTriangle, CheckCircle2, Loader2, Timer, XCircle } from "lucide-react";
import SqlBlock from "./SqlBlock";

export default function WriteConfirmCard({ message, onConfirm, onCancel }) {
  const { data, status, result, error } = message;
  const rows = data.row_count;
  const summary =
    rows != null
      ? `This will insert ${rows} row${rows === 1 ? "" : "s"} into `
      : "This will insert rows (count known after running) into ";

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-amber-200">
          <AlertTriangle className="h-4 w-4" aria-hidden /> Review before saving
        </p>
        <p className="mt-1 text-[15px] leading-relaxed">
          {summary}
          <span className="font-mono text-accent-soft">{data.table}</span>. Nothing is saved until you confirm.
        </p>
      </div>

      <SqlBlock sql={data.sql} />

      {status === "pending" && (
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={onConfirm} className="btn-primary">
            Confirm insert
          </button>
          <button onClick={onCancel} className="btn-ghost">
            Cancel
          </button>
          <span className="inline-flex items-center gap-1.5 text-xs text-mute">
            <Timer className="h-3.5 w-3.5" aria-hidden /> Expires in {Math.round(data.expires_in_seconds / 60)} min
          </span>
        </div>
      )}

      {status === "running" && (
        <p className="flex items-center gap-2 text-sm text-mute" role="status">
          <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden /> Saving...
        </p>
      )}

      {status === "done" && (
        <p className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          <CheckCircle2 className="h-4 w-4" aria-hidden /> {result.message} ({result.execution_time_ms} ms)
        </p>
      )}

      {status === "cancelled" && (
        <p className="flex items-center gap-2 text-sm text-mute">
          <XCircle className="h-4 w-4" aria-hidden /> Cancelled. Nothing was saved.
        </p>
      )}

      {status === "failed" && (
        <p className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {error}
        </p>
      )}
    </div>
  );
}
