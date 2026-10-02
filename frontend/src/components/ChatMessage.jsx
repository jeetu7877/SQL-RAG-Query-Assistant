import { AlertTriangle, Bot, User } from "lucide-react";
import SqlBlock from "./SqlBlock";
import ResultTable from "./ResultTable";

export default function ChatMessage({ message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-3">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-raised px-4 py-2.5 text-[15px] leading-relaxed">
          {message.text}
        </p>
        <div className="mt-0.5 hidden h-8 w-8 shrink-0 items-center justify-center rounded-full border border-line sm:flex">
          <User className="h-4 w-4 text-mute" aria-hidden />
        </div>
      </div>
    );
  }

  const d = message.data;
  return (
    <div className="flex gap-3">
      <div
        className={`mt-0.5 hidden h-8 w-8 shrink-0 items-center justify-center rounded-full sm:flex ${
          message.error ? "bg-red-500/15 text-red-300" : "bg-accent text-base"
        }`}
      >
        {message.error ? <AlertTriangle className="h-4 w-4" aria-hidden /> : <Bot className="h-4 w-4" aria-hidden />}
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        {message.error ? (
          <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-[15px] text-red-200">
            {message.text}
          </p>
        ) : (
          <>
            <p className="text-[15px] font-medium leading-relaxed">{d.answer}</p>
            <SqlBlock sql={d.sql} />
            <ResultTable
              columns={d.columns}
              rows={d.rows}
              rowCount={d.row_count}
              executionTimeMs={d.execution_time_ms}
              truncated={d.truncated}
            />
          </>
        )}
      </div>
    </div>
  );
}
