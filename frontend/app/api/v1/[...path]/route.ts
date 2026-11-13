import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const resources = new Set(["focus-sessions", "courses", "users", "sessions", "notes", "goals", "study-sessions", "timers",
  "data-exports", "deleted-resources", "reminders", "preferences", "dashboards", "data-resets", "health", "docs", "openapi.json"]);
type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: Context): Promise<Response> {
  const { path } = await context.params;
  if (!resources.has(path[0]) || path.some((part) => part === "." || part === ".." || /[\\/\u0000-\u001f]/.test(part))) {
    return Response.json({ ok: false, error: "API resource not found." }, { status: 404 });
  }
  let target: URL;
  try {
    if (process.env.NODE_ENV === "production" && !process.env.BACKEND_URL) throw new Error("Missing backend target");
    target = new URL(process.env.BACKEND_URL ?? "http://127.0.0.1:8000");
  } catch {
    return Response.json({ ok: false, error: "API proxy configuration is invalid." }, { status: 503 });
  }
  if (!["http:", "https:"].includes(target.protocol) || target.username || target.password ||
      target.pathname !== "/" || target.search || target.hash) {
    return Response.json({ ok: false, error: "API proxy configuration is invalid." }, { status: 503 });
  }
  target.pathname = `/api/v1/${path.map(encodeURIComponent).join("/")}`;
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["content-type", "cookie", "origin"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  // Trust this header only when the ingress overwrites client-supplied values.
  if (process.env.TRUST_PROXY_HEADERS === "true") {
    const address = request.headers.get("x-forwarded-for");
    if (address) headers.set("x-forwarded-for", address);
  }
  try {
    const bodyLimit = Number(process.env.MAX_REQUEST_BYTES ?? 524288);
    if (!Number.isInteger(bodyLimit) || bodyLimit < 1024 || bodyLimit > 10485760) throw new Error("Invalid body limit");
    let body: Uint8Array | undefined;
    if (!["GET", "HEAD"].includes(request.method)) {
      const chunks: Uint8Array[] = [];
      let size = 0;
      const reader = request.body?.getReader();
      if (reader) {
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          size += chunk.value.byteLength;
          if (size > bodyLimit) {
            await reader.cancel();
            return Response.json({ ok: false, error: "Request body is too large." }, { status: 413 });
          }
          chunks.push(chunk.value);
        }
      }
      body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    }
    const upstream = await fetch(target, { method: request.method, headers,
      body: body as BodyInit | undefined, cache: "no-store", redirect: "manual",
      signal: AbortSignal.timeout(30000) });
    const output = new Headers();
    for (const name of ["content-type", "content-disposition", "location", "retry-after", "x-request-id", "www-authenticate"] ) {
      const value = upstream.headers.get(name);
      if (value) {
        output.set(name, name === "location" && value.startsWith(target.origin)
          ? value.replace(target.origin, request.nextUrl.origin) : value);
      }
    }
    for (const cookie of upstream.headers.getSetCookie()) output.append("set-cookie", cookie);
    output.set("cache-control", "no-store");
    return new Response(upstream.status === 204 ? null : upstream.body,
      { status: upstream.status, headers: output });
  } catch {
    return Response.json({ ok: false, error: "The API is temporarily unavailable." },
      { status: 503, headers: { "cache-control": "no-store" } });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
