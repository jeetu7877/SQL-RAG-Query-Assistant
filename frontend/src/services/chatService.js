import api from "./api";

export const askQuestion = (question) =>
  api.post("/api/chat", { question }).then((r) => r.data);
