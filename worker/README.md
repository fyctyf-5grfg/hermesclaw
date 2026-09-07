# Hermes WebUI Worker

This Worker is the public entrypoint for the temporary Hermes WebUI tunnel.

- If the URL in `webui-url.txt` responds successfully, the Worker redirects to it.
- If it is unreachable, the Worker checks for an active workflow first. It dispatches `hermes-webui.yml` only when no run is queued or in progress.

Deploy from this directory:

```bash
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

`GITHUB_TOKEN` must be a fine-grained token with Actions `Read and write` access for this repository. The workflow writes each new quick-tunnel URL to `webui-url.txt`, so no URL secret needs manual updating.

Stop all active WebUI runs by visiting:

https://hermes-webui-redirect.kahibexi.workers.dev/stop

The Worker uses its configured `GITHUB_TOKEN` internally. This endpoint is intentionally public: anyone who knows the URL can stop active WebUI runs.