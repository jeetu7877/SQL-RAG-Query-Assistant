import axios from "axios";

const KEY = "pg_text2sql_connection";

export const getStoredConnection = () => {
  try {
    return JSON.parse(sessionStorage.getItem(KEY));
  } catch {
    return null;
  }
};
export const storeConnection = (c) => sessionStorage.setItem(KEY, JSON.stringify(c));
export const clearStoredConnection = () => sessionStorage.removeItem(KEY);

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 60000,
});

// attach the active session id (the DB password never reaches the browser after connect)
api.interceptors.request.use((config) => {
  const conn = getStoredConnection();
  if (conn?.connection_id) config.headers["X-Connection-ID"] = conn.connection_id;
  return config;
});

// normalize errors to { message, status }
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const status = error.response?.status;
    let message = error.response?.data?.detail;

    // Export endpoints return application/json errors even though successful
    // downloads use responseType: "blob". Decode those errors here.
    if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text();
        const parsed = JSON.parse(text);
        message = parsed.detail;
      } catch {
        // Keep the generic fallback below.
      }
    }

    if (typeof message !== "string") {
      message = error.response
        ? "Something went wrong. Please try again."
        : "Cannot reach the server. Check that the backend is running.";
    }
    if (status === 401) window.dispatchEvent(new Event("session-expired"));
    return Promise.reject({ message, status });
  }
);

export default api;
