import api from "./api";

export const connectDatabase = (database_url) =>
  api.post("/api/database/connect", { database_url }).then((r) => r.data);

export const disconnectDatabase = () =>
  api.post("/api/database/disconnect").then((r) => r.data);

export const fetchSchema = (refresh = false) =>
  api.get("/api/database/schema", { params: { refresh } }).then((r) => r.data);

export const downloadDatabaseExport = async (
  format = "xlsx",
  table = null
) => {
  const params = {
    format,
    _t: Date.now(),
  };

  if (table) {
    params.table = table;
  }

  const response = await api.get("/api/database/export", {
    params,
    responseType: "blob",
  });

  const contentType = response.headers["content-type"] || "";

  if (contentType.includes("application/json")) {
    const text = await response.data.text();

    try {
      const parsed = JSON.parse(text);
      throw new Error(parsed.detail || "Export failed.");
    } catch (err) {
      if (err instanceof Error && err.message !== text) {
        throw err;
      }

      throw new Error("Export failed.");
    }
  }

  const disposition =
    response.headers["content-disposition"] || "";

  const match = disposition.match(
    /filename="?([^";]+)"?/i
  );

  const fallback = table
    ? `${table}.${format}`
    : format === "csv"
      ? "database_csv_export.zip"
      : "database_export.xlsx";

  const filename = match?.[1] || fallback;

  const url = window.URL.createObjectURL(response.data);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;

  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(() => {
    window.URL.revokeObjectURL(url);
  }, 1000);
};
