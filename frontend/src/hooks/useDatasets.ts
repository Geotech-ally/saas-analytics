import { useState, useEffect, useCallback } from "react";
import { datasetsService } from "../services/api";
import type { Dataset } from "../types";

export function useDatasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await datasetsService.list();
      setDatasets(data.results ?? data);
    } catch {
      setError("Failed to load datasets.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const upload = async (file: File, name: string, description = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    form.append("description", description);
    const created = await datasetsService.upload(form);
    setDatasets((prev) => [created, ...prev]);
    return created;
  };

  const remove = async (id: string) => {
    await datasetsService.delete(id);
    setDatasets((prev) => prev.filter((d) => d.id !== id));
  };

  return { datasets, loading, error, refetch: fetchDatasets, upload, remove };
}
