# Hermes WebUI Worker

This Worker is the public entrypoint for the temporary Hermes WebUI tunnel.

- If the URL in `webui-url.txt` responds successfully, the Worker redirects to it.
- If it is unreachable, the Worker dispatches `hermes-webui.yml` on `main` and returns `202`.

Deploy from this directory:

```bash
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put STOP_TOKEN
npx wrangler deploy
```

`GITHUB_TOKEN` must be a fine-grained token with Actions `Read and write` access for this repository. The workflow writes each new quick-tunnel URL to `webui-url.txt`, so no URL secret needs manual updating.

Stop all active WebUI runs with the `STOP_TOKEN` secret:

```bash
curl -X POST -H "Authorization: Bearer YOUR_STOP_TOKEN" https://your-worker.workers.dev/stop
```