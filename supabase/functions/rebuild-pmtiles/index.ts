Deno.serve(async (request) => {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const expectedSecret = Deno.env.get("WEBHOOK_SECRET");
  const suppliedSecret = request.headers.get("x-webhook-secret");
  if (!expectedSecret || suppliedSecret !== expectedSecret) {
    return new Response("Unauthorized", { status: 401 });
  }

  let payload: { schema?: string; table?: string; type?: string };
  try {
    payload = await request.json();
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  if (payload.schema !== "public" || payload.table !== "gebaeude_stp") {
    return new Response("Unexpected table", { status: 400 });
  }
  if (!payload.type || !["INSERT", "UPDATE", "DELETE"].includes(payload.type)) {
    return new Response("Unsupported database event", { status: 400 });
  }

  const repository = Deno.env.get("GITHUB_REPOSITORY");
  const githubToken = Deno.env.get("GITHUB_TOKEN");
  if (!repository || !githubToken) {
    return new Response("GitHub integration is not configured", { status: 500 });
  }

  const githubResponse = await fetch(
    `https://api.github.com/repos/${repository}/dispatches`,
    {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${githubToken}`,
        "Content-Type": "application/json",
        "User-Agent": "supabase-pmtiles-webhook",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        event_type: "gebaeude-stp-changed",
        client_payload: { table: payload.table, operation: payload.type },
      }),
    },
  );

  if (!githubResponse.ok) {
    console.error("GitHub dispatch failed with status", githubResponse.status);
    return new Response("GitHub dispatch failed", { status: 502 });
  }

  return Response.json({ dispatched: true });
});