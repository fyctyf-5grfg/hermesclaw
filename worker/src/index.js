const WORKFLOW_FILE = "hermes-webui.yml";
const HEALTH_TIMEOUT_MS = 5000;

function response(body, status, headers = {}) {
  return new Response(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      ...headers,
    },
  });
}

async function webuiIsReachable(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const result = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
    });
    return result.status >= 200 && result.status < 500;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function currentWebuiUrl(env) {
  const result = await fetch(`${env.WEBUI_URL_FILE}?t=${Date.now()}`, {
    headers: {
      Accept: "application/vnd.github.raw+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Cache-Control": "no-cache",
      "User-Agent": "hermes-webui-worker",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!result.ok) {
    return null;
  }
  const value = (await result.text()).trim();
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

async function dispatchWebui(env) {
  const endpoint = `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${WORKFLOW_FILE}/dispatches`;
  const result = await fetch(endpoint, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "hermes-webui-worker",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: env.GITHUB_REF || "main" }),
  });

  if (!result.ok) {
    const details = await result.text();
    throw new Error(`GitHub dispatch failed (${result.status}): ${details}`);
  }
}

async function stopWebuiRuns(env) {
  const api = `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=100`;
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    "User-Agent": "hermes-webui-worker",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  const listing = await fetch(api, { headers });
  if (!listing.ok) {
    throw new Error(`GitHub run listing failed (${listing.status})`);
  }
  const data = await listing.json();
  const activeRuns = (data.workflow_runs || []).filter((run) =>
    run.status === "queued" || run.status === "in_progress",
  );
  const results = await Promise.all(activeRuns.map(async (run) => {
    const cancel = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/actions/runs/${run.id}/cancel`,
      { method: "POST", headers },
    );
    return { id: run.id, cancelled: cancel.ok };
  }));
  return results;
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname === "/stop") {
      if (request.method !== "GET" && request.method !== "POST") {
        return response("Method not allowed", 405, { Allow: "GET, POST" });
      }
      if (!env.GITHUB_TOKEN || !env.GITHUB_REPOSITORY) {
        return response("Worker is not configured", 503);
      }
      try {
        const runs = await stopWebuiRuns(env);
        return response(JSON.stringify({ stopped: runs }), 200, {
          "Content-Type": "application/json",
        });
      } catch (error) {
        return response(error.message, 502, { "Content-Type": "text/plain; charset=utf-8" });
      }
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return response("Method not allowed", 405, { Allow: "GET, HEAD" });
    }

    const missing = [
      !env.WEBUI_URL_FILE && "WEBUI_URL_FILE",
      !env.GITHUB_TOKEN && "GITHUB_TOKEN",
      !env.GITHUB_REPOSITORY && "GITHUB_REPOSITORY",
    ].filter(Boolean);
    if (missing.length) {
      return response(`Worker is not configured: missing ${missing.join(", ")}`, 503);
    }

    const webuiUrl = await currentWebuiUrl(env);
    if (webuiUrl && await webuiIsReachable(webuiUrl)) {
      return Response.redirect(webuiUrl, 302);
    }

    try {
      await dispatchWebui(env);
    } catch (error) {
      return response(error.message, 502, { "Content-Type": "text/plain; charset=utf-8" });
    }

    return response(
      "Hermes WebUI was offline, so a new workflow run was started. Refresh this URL in a few minutes.",
      202,
      {
        "Content-Type": "text/plain; charset=utf-8",
        "Retry-After": "30",
      },
    );
  },
};