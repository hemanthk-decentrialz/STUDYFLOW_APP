"use client";

import { useEffect, useState } from "react";
import { notify } from "@/components/ui/DataSyncStatus";
import { useAuth } from "@/context/AuthContext";
import { ResourceApi, ResourceInput, ResourcePage, ResourceQuery, restoreResource } from "@/lib/api/resources";

export default function useResourceList<T extends { id: number }, Patch = Partial<Omit<T, "id">>>(api: ResourceApi<T> & { patch?: (id: number, payload: Patch) => Promise<T> }, initialQuery: ResourceQuery = {}) {
  const { user, isLoading: authLoading } = useAuth();
  const [query, setQuery] = useState<ResourceQuery>({ page: 1, limit: 10, sort_by: "position", order: "asc", ...initialQuery });
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ userId: string; data: ResourcePage<T> } | null>(null);

  useEffect(() => {
    if (!user || authLoading) return;
    const controller = new AbortController();
    let active = true;
    const load = async () => {
      setLoading(true);
      try {
        const data = await api.list(query, controller.signal);
        if (!active) return;
        const lastPage = Math.max(1, data.total_pages);
        if ((query.page ?? 1) > lastPage) {
          setQuery((previous) => ({ ...previous, page: lastPage }));
          return;
        }
        setResult({ userId: user.id, data });
        setError(null);
      } catch (failure) {
        if (active) setError(failure instanceof Error ? failure.message : "Unable to load resources.");
      } finally { if (active) setLoading(false); }
    };
    void load();
    return () => { active = false; controller.abort(); };
  }, [api, query, revision, user, authLoading]);

  async function mutate<R>(operation: () => Promise<R>): Promise<R> {
    setPending((previous) => previous + 1);
    try {
      const saved = await operation();
      setRevision((previous) => previous + 1);
      window.dispatchEvent(new Event("studyflow-data-saved"));
      setError(null);
      return saved;
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to save changes.");
      throw failure;
    } finally { setPending((previous) => previous - 1); }
  }

  useEffect(() => { const refresh = () => setRevision((value) => value + 1); window.addEventListener("studyflow-resource-restored", refresh); return () => window.removeEventListener("studyflow-resource-restored", refresh); }, []);
  const data = result?.userId === user?.id ? result?.data : undefined;
  return {
    items: data?.items ?? [], data, query, setQuery, loading: loading || authLoading || pending > 0, error,
    retry: () => setRevision((previous) => previous + 1),
    create: (payload: ResourceInput<T>) => mutate(() => api.create(payload)),
    patch: async (id: number, payload: Patch) => {
      if (!api.patch) throw new Error("Editing is not available for this resource.");
      const patch = api.patch;
      const saved = await mutate(() => patch(id, payload));
      setResult((previous) => previous ? { ...previous, data: { ...previous.data,
        items: previous.data.items.map((item) => item.id === id ? saved : item) } } : previous);
      return saved;
    },
    replace: (saved: T) => setResult((previous) => previous ? { ...previous, data: { ...previous.data, items: previous.data.items.map((item) => item.id === saved.id ? saved : item) } } : previous),
    remove: async (id: number) => {
      await mutate(() => api.remove(id));
      notify("Item deleted.", { action: { label: "Undo", run: async () => {
        await mutate(() => restoreResource<T>(api.module, id));
        window.dispatchEvent(new Event("studyflow-resource-restored"));
      } } });
    },
  };
}
