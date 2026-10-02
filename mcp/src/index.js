/**
 * MCP server for austinbrian.github.io.
 *
 * Built against the 2026-07-28 MCP revision, which removed the `initialize`
 * handshake and the `Mcp-Session-Id` header: every request stands alone, so this
 * is an ordinary stateless HTTP handler with no storage and no affinity. The
 * older 2025-06-18 flow is still accepted, because most deployed clients speak
 * it — `initialize` is handled rather than rejected.
 *
 * Content is NOT baked in here. It is fetched from /mcp-content.json, which the
 * Jekyll build generates from _data/mcp.yml. Editing the site and
 * pushing to master is enough; this Worker only needs redeploying when the tool
 * surface itself changes.
 */

const SUPPORTED_PROTOCOLS = ["2026-07-28", "2025-06-18", "2025-03-26"];
const PREFERRED_PROTOCOL = "2026-07-28";

const SERVER_INFO = {
  name: "io.github.austinbrian/website",
  title: "Brian Austin — personal site",
  version: "1.0.0",
};

const INSTRUCTIONS = [
  "Read-only access to Brian Austin's personal site: profile, projects, and running data.",
  "Start with get_profile.",
].join(" ");

/* ---------------------------------------------------------------- content */

// Cloudflare's edge cache does the real work here; this only avoids refetching
// within a single invocation when several tools need the same document.
let contentPromise = null;

function fetchJson(url, ttl) {
  return fetch(url, {
    headers: { accept: "application/json" },
    cf: { cacheTtl: ttl, cacheEverything: true },
  }).then((res) => {
    if (!res.ok) throw new Error(`${url} responded ${res.status}`);
    return res.json();
  });
}

function loadContent(env) {
  if (!contentPromise) {
    contentPromise = fetchJson(env.CONTENT_URL, 300).catch((err) => {
      contentPromise = null; // don't cache a failure for the life of the isolate
      throw err;
    });
  }
  return contentPromise;
}

/* ------------------------------------------------------------------ tools */

const TOOLS = [
  {
    name: "get_profile",
    title: "Get profile",
    description:
      "Brian Austin's bio, location, current role, focus areas, technical toolkit, certifications, and contact links. The best first call for understanding who he is and what he works on.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "list_projects",
    title: "List projects",
    description:
      "Projects worth looking at, each with a tagline, a full description, a URL, and links to related source repositories or talks.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "get_running_stats",
    title: "Get running stats",
    description:
      "Aggregate running statistics over a recent window — run count, distance, time, average pace, elevation, and the longest single run — computed from Strava data synced nightly to Cloudflare R2.",
    inputSchema: {
      type: "object",
      properties: {
        days: {
          type: "integer",
          description: "Size of the lookback window in days. Defaults to 90.",
          minimum: 1,
          maximum: 3650,
        },
      },
      additionalProperties: false,
    },
  },
];

function textResult(text, structured) {
  const result = { content: [{ type: "text", text }] };
  if (structured !== undefined) result.structuredContent = structured;
  return result;
}

async function callTool(name, args, env) {
  switch (name) {
    case "get_profile": {
      const { profile } = await loadContent(env);
      return textResult(renderProfile(profile), profile);
    }

    case "list_projects": {
      const { projects } = await loadContent(env);
      return textResult(renderProjects(projects), { projects });
    }

    case "get_running_stats": {
      const days = args?.days ?? 90;
      const activities = await fetchJson(env.RUNNING_DATA_URL, 900);
      const cutoff = Date.now() - days * 86400000;
      const runs = activities.filter(
        (a) => a.type === "Run" && Date.parse(a.start_date) >= cutoff,
      );

      if (runs.length === 0) {
        return textResult(`No runs recorded in the last ${days} days.`, {
          days,
          run_count: 0,
        });
      }

      const miles = runs.reduce((sum, r) => sum + (r.distance_miles || 0), 0);
      const minutes = runs.reduce((sum, r) => sum + (r.moving_time_minutes || 0), 0);
      const feet = runs.reduce((sum, r) => sum + (r.elevation_feet || 0), 0);
      const longest = runs.reduce((a, b) =>
        (a.distance_miles || 0) >= (b.distance_miles || 0) ? a : b,
      );
      const hr = runs.filter((r) => r.has_heartrate && r.average_heartrate);

      const stats = {
        window_days: days,
        run_count: runs.length,
        total_miles: round(miles, 1),
        total_hours: round(minutes / 60, 1),
        average_pace_min_per_mile: formatPace(minutes / miles),
        average_miles_per_week: round(miles / (days / 7), 1),
        total_elevation_feet: Math.round(feet),
        average_heartrate: hr.length
          ? Math.round(hr.reduce((s, r) => s + r.average_heartrate, 0) / hr.length)
          : null,
        longest_run: {
          name: longest.name,
          date: longest.start_date_local.slice(0, 10),
          miles: round(longest.distance_miles, 2),
          pace_min_per_mile: formatPace(longest.moving_time_minutes / longest.distance_miles),
        },
        source: "https://austinbrian.github.io/running/",
      };

      const text = [
        `Running, last ${days} days:`,
        `- ${stats.run_count} runs, ${stats.total_miles} miles, ${stats.total_hours} hours`,
        `- ${stats.average_miles_per_week} miles/week at ${stats.average_pace_min_per_mile}/mile average`,
        `- ${stats.total_elevation_feet.toLocaleString("en-US")} ft climbed`,
        stats.average_heartrate ? `- Average heart rate ${stats.average_heartrate} bpm` : null,
        `- Longest: ${stats.longest_run.miles} mi on ${stats.longest_run.date} at ${stats.longest_run.pace_min_per_mile}/mile`,
        "",
        `Charts: ${stats.source}`,
      ]
        .filter((line) => line !== null)
        .join("\n");

      return textResult(text, stats);
    }

    default:
      return null; // signals "unknown tool" to the caller
  }
}

const round = (n, places) => Number(n.toFixed(places));

function formatPace(minutesPerMile) {
  if (!isFinite(minutesPerMile) || minutesPerMile <= 0) return "n/a";
  const whole = Math.floor(minutesPerMile);
  const seconds = Math.round((minutesPerMile - whole) * 60);
  return seconds === 60 ? `${whole + 1}:00` : `${whole}:${String(seconds).padStart(2, "0")}`;
}

/* --------------------------------------------------------------- renderers */

function renderProfile(p) {
  const lines = [
    `# ${p.name}`,
    `${p.title} · ${p.location}`,
    ``,
    p.summary,
    ``,
    `## Current role`,
    `${p.current_role.title}, ${p.current_role.org} (since ${p.current_role.started})`,
    p.current_role.description,
    ``,
    `## Focus`,
    ...p.focus.map((f) => `- ${f}`),
    ``,
    `## Toolkit`,
    ...Object.entries(p.toolkit).map(([k, v]) => `- ${k}: ${v}`),
    ``,
    `## Certifications`,
    ...p.certifications.map((c) => `- ${c}`),
    ``,
    `## Links`,
    ...Object.entries(p.links).map(([k, v]) => `- ${k}: ${v}`),
  ];
  return lines.join("\n");
}

function renderProjects(projects) {
  return projects
    .map((project) => {
      const parts = [`## ${project.name}`, `_${project.tagline}_`, ``, project.description];
      if (project.url) parts.push(``, `URL: ${project.url}`);
      for (const link of project.related || []) parts.push(`${link.name}: ${link.url}`);
      return parts.join("\n");
    })
    .join("\n\n---\n\n");
}

/* --------------------------------------------------------------- resources */

function resourceList(env) {
  return [
    {
      uri: `${env.SITE_URL}/sitemap.xml`,
      name: "sitemap",
      title: "Site map",
      description: "Every published URL on austinbrian.github.io.",
      mimeType: "application/xml",
    },
    {
      uri: `${env.SITE_URL}/llms.txt`,
      name: "llms.txt",
      title: "Site summary for agents",
      description: "Structured plain-text overview of the site and its projects.",
      mimeType: "text/plain",
    },
    {
      uri: "mcp://server-card.json",
      name: "server-card",
      title: "MCP server card",
      description: "This server's own capability card.",
      mimeType: "application/json",
    },
  ];
}

async function readResource(uri, env) {
  const known = resourceList(env).find((r) => r.uri === uri);
  if (!known) return null;

  const target =
    uri === "mcp://server-card.json" ? `${env.SITE_URL}/.well-known/mcp/server-card.json` : uri;

  const res = await fetch(target, { cf: { cacheTtl: 300, cacheEverything: true } });
  if (!res.ok) throw new Error(`${target} responded ${res.status}`);

  return { contents: [{ uri, mimeType: known.mimeType, text: await res.text() }] };
}

/* ------------------------------------------------------------------ JSON-RPC */

const ok = (id, result) => ({ jsonrpc: "2.0", id, result });
const fail = (id, code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });

async function dispatch(request, env) {
  const { id, method, params } = request;

  switch (method) {
    case "initialize": {
      // Gone in 2026-07-28, still sent by clients on older revisions.
      const asked = params?.protocolVersion;
      return ok(id, {
        protocolVersion: SUPPORTED_PROTOCOLS.includes(asked) ? asked : PREFERRED_PROTOCOL,
        capabilities: { tools: { listChanged: false }, resources: { listChanged: false } },
        serverInfo: SERVER_INFO,
        instructions: INSTRUCTIONS,
      });
    }

    case "ping":
      return ok(id, {});

    case "tools/list":
      return ok(id, {
        tools: TOOLS,
        // 2026-07-28: catalogs are cacheable and returned in a deterministic order.
        ttlMs: 3_600_000,
        cacheScope: "server",
      });

    case "tools/call": {
      const name = params?.name;
      try {
        const result = await callTool(name, params?.arguments, env);
        if (result === null) return fail(id, -32602, `Unknown tool: ${name}`);
        return ok(id, result);
      } catch (err) {
        // Tool failures belong in the result, not the protocol error channel,
        // so the model can see them and adapt.
        return ok(id, {
          content: [{ type: "text", text: `Tool "${name}" failed: ${err.message}` }],
          isError: true,
        });
      }
    }

    case "resources/list":
      return ok(id, { resources: resourceList(env) });

    case "resources/read": {
      try {
        const contents = await readResource(params?.uri, env);
        if (contents === null) return fail(id, -32602, `Unknown resource: ${params?.uri}`);
        return ok(id, contents);
      } catch (err) {
        return fail(id, -32603, err.message);
      }
    }

    case "prompts/list":
      return ok(id, { prompts: [] });

    case "resources/templates/list":
      return ok(id, { resourceTemplates: [] });

    default:
      return fail(id, -32601, `Method not found: ${method}`);
  }
}

/* ---------------------------------------------------------------- transport */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers":
    "Content-Type, Accept, Authorization, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Mcp-Session-Id",
  "Access-Control-Expose-Headers": "MCP-Protocol-Version",
  "Access-Control-Max-Age": "86400",
};

function json(body, init = {}) {
  return new Response(JSON.stringify(body, null, 2), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "MCP-Protocol-Version": PREFERRED_PROTOCOL,
      ...CORS,
      ...init.headers,
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    // Serve the card from the Worker's own origin too, so a client holding only
    // the endpoint URL can still discover what this is.
    if (url.pathname === "/.well-known/mcp/server-card.json") {
      const res = await fetch(`${env.SITE_URL}/.well-known/mcp/server-card.json`, {
        cf: { cacheTtl: 300, cacheEverything: true },
      });
      return new Response(res.body, {
        status: res.status,
        headers: { "Content-Type": "application/json", ...CORS },
      });
    }

    if (request.method === "GET") {
      return json({
        name: SERVER_INFO.title,
        description: INSTRUCTIONS,
        transport: "streamable-http",
        endpoint: `${url.origin}/mcp`,
        protocolVersions: SUPPORTED_PROTOCOLS,
        serverCard: `${url.origin}/.well-known/mcp/server-card.json`,
        website: env.SITE_URL,
        note: "This endpoint speaks MCP over JSON-RPC. POST to /mcp.",
      });
    }

    if (request.method !== "POST" || url.pathname !== "/mcp") {
      return json(fail(null, -32600, "POST JSON-RPC to /mcp."), { status: 404 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json(fail(null, -32700, "Parse error: body is not valid JSON."), { status: 400 });
    }

    // A batch is an array; a notification has no `id` and takes no response.
    const batch = Array.isArray(body) ? body : [body];
    const responses = [];

    for (const message of batch) {
      if (!message || message.jsonrpc !== "2.0" || typeof message.method !== "string") {
        responses.push(fail(message?.id ?? null, -32600, "Invalid JSON-RPC request."));
        continue;
      }
      if (message.id === undefined || message.id === null) continue; // notification
      responses.push(await dispatch(message, env));
    }

    if (responses.length === 0) return new Response(null, { status: 202, headers: CORS });

    return json(Array.isArray(body) ? responses : responses[0]);
  },
};
