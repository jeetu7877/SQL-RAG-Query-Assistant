import { Loader2 } from "lucide-react";

export default function LoadingSpinner({ label, className = "" }) {
  return (
    <div className={`flex items-center justify-center gap-2 text-mute ${className}`} role="status">
      <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
