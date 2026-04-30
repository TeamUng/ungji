const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const backendBaseUrl =
    process.env.UNGJI_API_BASE_URL ?? DEFAULT_BACKEND_BASE_URL;
  const body = await request.text();

  const upstream = await fetch(`${backendBaseUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body,
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") ?? "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}
