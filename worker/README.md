# Hermes WebUI Worker

This Worker is the public entrypoint for the temporary Hermes WebUI tunnel.

- If `HERMES_WEBUI_URL` responds successfully, the Worker redirects to it.
- If it is unreachable, the Worker dispatches `hermes-webui.yml` on `main` and returns `202`.

Deploy from this directory:

```bash
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put HERMES_WEBUI_URL
npx wrangler deploy
```

`GITHUB_TOKEN` must be a fine-grained token with Actions `Read and write` access for this repository. Update `HERMES_WEBUI_URL` after each new temporary tunnel URL is created.