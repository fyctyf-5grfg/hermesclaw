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

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return response("Method not allowed", 405, { Allow: "GET, HEAD" });
    }

    if (!env.HERMES_WEBUI_URL || !env.GITHUB_TOKEN || !env.GITHUB_REPOSITORY) {
      return response("Worker is not configured", 503);
    }

    if (await webuiIsReachable(env.HERMES_WEBUI_URL)) {
      return Response.redirect(env.HERMES_WEBUI_URL, 302);
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