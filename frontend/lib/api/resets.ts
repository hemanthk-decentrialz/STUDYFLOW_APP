import { apiRequest } from "./client";

export interface ResetJob {
  id: string; kind: "study-data-reset"; status: "queued" | "running" | "completed" | "failed";
  created_at: string; completed_at: string | null; error: string | null;
}

export function currentReset(): Promise<ResetJob | null> {
  return apiRequest<ResetJob | null>("/api/v1/data-resets/current");
}

export async function waitForReset(id: string): Promise<void> {
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline) {
    const job = await currentReset();
    if (!job || job.id !== id) {
      throw new Error("The reset status changed. Reload the app to check the current reset.");
    }
    if (job.status === "completed") return;
    if (job.status === "failed") throw new Error(job.error ?? "Reset failed. Please try again.");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("Reset is still processing. Its progress will be restored when you reopen the app.");
}

export async function requestReset(): Promise<void> {
  const job = await apiRequest<ResetJob>("/api/v1/data-resets", { method: "POST" });
  await waitForReset(job.id);
}
