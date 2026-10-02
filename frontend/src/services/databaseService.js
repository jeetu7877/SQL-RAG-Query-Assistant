import api from "./api";

export const connectDatabase = (database_url) =>
  api.post("/api/database/connect", { database_url }).then((r) => r.data);

export const disconnectDatabase = () =>
  api.post("/api/database/disconnect").then((r) => r.data);

export const fetchSchema = (refresh = false) =>
  api.get("/api/database/schema", { params: { refresh } }).then((r) => r.data);
