import { useState } from "react";
import { Check, Copy } from "lucide-react";

const KEYWORDS = new Set(
  `SELECT FROM WHERE GROUP BY ORDER HAVING LIMIT OFFSET JOIN LEFT RIGHT INNER OUTER FULL CROSS ON AS AND OR NOT IN IS NULL
   LIKE ILIKE BETWEEN CASE WHEN THEN ELSE END DISTINCT UNION ALL WITH ASC DESC EXISTS INTERVAL OVER PARTITION FILTER
   CAST TRUE FALSE USING`.split(/\s+/)
);
const FUNCTIONS = new Set(
  "COUNT SUM AVG MIN MAX ROUND COALESCE DATE_TRUNC EXTRACT LOWER UPPER LENGTH NOW CURRENT_DATE ROW_NUMBER RANK".split(" ")
);

// tiny tokenizer: comments, strings, quoted identifiers, numbers, words, everything else
const TOKEN = /(--[^\n]*)|('(?:[^']|'')*')|("(?:[^"]|"")*")|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+|.)/g;

function highlight(sql) {
  const out = [];
  let m;
  let i = 0;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(sql)) !== null) {
    const [tok, comment, str, ident, num, word] = m;
    let cls = "";
    if (comment) cls = "text-mute italic";
    else if (str) cls = "text-emerald-300";
    else if (ident) cls = "text-sky-300";
    else if (num) cls = "text-amber-300";
    else if (word) {
      const up = word.toUpperCase();
      if (KEYWORDS.has(up)) cls = "text-accent-soft font-medium";
      else if (FUNCTIONS.has(up)) cls = "text-violet-300";
    }
    out.push(
      cls ? (
        <span key={i++} className={cls}>
          {tok}
        </span>
      ) : (
        tok
      )
    );
  }
  return out;
}

export default function SqlBlock({ sql }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable (non-secure context) */
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-line bg-base">
      <div className="flex items-center justify-between border-b border-line px-3.5 py-2">
        <span className="text-xs font-medium text-mute">Generated SQL</span>
        <button
          onClick={copy}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-mute transition-colors hover:bg-raised hover:text-ink"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy SQL"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3.5 font-mono text-[13px] leading-relaxed text-ink">
        <code>{highlight(sql)}</code>
      </pre>
    </div>
  );
}
