import { NavLink } from "react-router-dom";
import { Database, LogOut, MessageSquare, Network } from "lucide-react";
import { useConnection } from "../context/ConnectionContext";

const linkClass = ({ isActive }) =>
  `inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors ${
    isActive ? "bg-raised text-ink" : "text-mute hover:text-ink"
  }`;

export default function Navbar() {
  const { connection, disconnect } = useConnection();

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-panel px-4">
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-base">
          <Database className="h-5 w-5" aria-hidden />
        </div>
        <span className="hidden truncate text-sm font-semibold md:block">PostgreSQL Text-to-SQL Assistant</span>
      </div>

      <nav className="ml-2 flex items-center gap-1" aria-label="Main">
        <NavLink to="/" end className={linkClass}>
          <MessageSquare className="h-4 w-4" aria-hidden /> Chat
        </NavLink>
        <NavLink to="/schema" className={linkClass}>
          <Network className="h-4 w-4" aria-hidden /> Schema
        </NavLink>
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <span className="hidden items-center gap-2 rounded-full border border-line px-3 py-1 text-xs sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden />
          <span className="text-mute">Connected</span>
          <span className="max-w-[140px] truncate font-medium">{connection.database_name}</span>
        </span>
        <button onClick={disconnect} className="btn-ghost !px-3 !py-1.5">
          <LogOut className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">Disconnect</span>
        </button>
      </div>
    </header>
  );
}
