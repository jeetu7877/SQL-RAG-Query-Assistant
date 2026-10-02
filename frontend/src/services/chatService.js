import api from "./api";

export const askQuestion = (question) =>
  api.post("/api/chat", { question }).then((r) => r.data);

// ---- write mode (INSERT only): preview first, then an explicit confirm ----
export const previewWrite = (question) =>
  api.post("/api/write/preview", { question }).then((r) => r.data);

export const confirmWrite = (token) =>
  api.post("/api/write/confirm", { token }).then((r) => r.data);

export const cancelWrite = (token) =>
  api.post("/api/write/cancel", { token }).then((r) => r.data);

export const getServerInfo = () => api.get("/api/health").then((r) => r.data);
