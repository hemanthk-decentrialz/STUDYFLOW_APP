import { ApiResponse } from "@/types/api";

let sessionGeneration = 0;

export function invalidateApiRequests(): void {
  sessionGeneration++;
}

interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  responseType?: "blob";
}

export class ApiRequestError extends Error {
  status: number;
  details: string[];

  constructor(message: string, status: number, details: string[] = []) {
    super(details.length ? `${message} ${details.join(" ")}` : message);
    this.name = "ApiRequestError";
    this.status = status;
    this.details = details;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const requestGeneration = sessionGeneration;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  const response = await fetch(endpoint, {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    cache: "no-store",
    signal: options.signal,
    body:
      options.body === undefined
        ? undefined
        : JSON.stringify(options.body),
  });

  if (response.status === 204 && response.ok) return undefined as T;
  if (response.ok && options.responseType === "blob") return await response.blob() as T;

  const payload = (await response
    .json()
    .catch(() => ({
      ok: false,
      error: `API request failed with status ${response.status}.`,
    }))) as ApiResponse<T>;

  if (!response.ok || !payload.ok) {
    if (response.status === 401 && requestGeneration === sessionGeneration &&
      !endpoint.startsWith("/api/v1/sessions") && endpoint !== "/api/v1/users/me" && typeof window !== "undefined") {
      window.dispatchEvent(new Event("studyflow-session-expired"));
    }
    throw new ApiRequestError(
      !payload.ok ? payload.error : `API request failed with status ${response.status}.`,
      response.status,
      !payload.ok ? payload.details : undefined
    );
  }

  return payload.data;
}
