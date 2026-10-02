import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearStoredConnection, getStoredConnection, storeConnection } from "../services/api";
import { connectDatabase, disconnectDatabase } from "../services/databaseService";

const ConnectionContext = createContext(null);
export const useConnection = () => useContext(ConnectionContext);

export function ConnectionProvider({ children }) {
  const [connection, setConnection] = useState(getStoredConnection());

  // 1) talk to the backend; keeps only safe info (id, db name, host) in this tab
  const connect = useCallback(async (url) => {
    const info = await connectDatabase(url);
    storeConnection(info);
    return info;
  }, []);

  // 2) switch the UI into the connected state
  const activate = useCallback((info) => setConnection(info), []);

  const disconnect = useCallback(async () => {
    try {
      await disconnectDatabase();
    } catch {
      /* session may already be gone */
    }
    clearStoredConnection();
    setConnection(null);
  }, []);

  // backend says the session expired -> drop it
  useEffect(() => {
    const onExpired = () => {
      clearStoredConnection();
      setConnection(null);
    };
    window.addEventListener("session-expired", onExpired);
    return () => window.removeEventListener("session-expired", onExpired);
  }, []);

  const value = useMemo(() => ({ connection, connect, activate, disconnect }),
    [connection, connect, activate, disconnect]);
  return <ConnectionContext.Provider value={value}>{children}</ConnectionContext.Provider>;
}
