# HermesClaw

HermesClaw runs Hermes Agent in GitHub Actions for issue automation and a temporary WebUI session.

## Worker

Open the Worker URL to reach Hermes WebUI:

https://hermes-webui-redirect.kahibexi.workers.dev

If the WebUI tunnel is offline, the Worker starts `hermes-webui.yml` and returns a retry response. The workflow writes the new tunnel URL to [`webui-url.txt`](webui-url.txt).

Stop all active WebUI workflows:

https://hermes-webui-redirect.kahibexi.workers.dev/stop

The `/stop` URL is public. Anyone who knows it can stop active WebUI runs.

## Setup

Add these repository secrets:

- `TOKEN`: GitHub token with Contents, Actions, Packages, and Workflows write access.
- `OPENAI_API_KEY`: model provider credential.

The Worker stores the same GitHub token as `GITHUB_TOKEN`. Deploy it with:

```bash
cd worker
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

## Workflows

- [`hermes-bot.yml`](.github/workflows/hermes-bot.yml) responds to authorized issue and issue-comment events.
- [`hermes-webui.yml`](.github/workflows/hermes-webui.yml) installs Hermes, starts the WebUI and Cloudflare tunnel, publishes its URL, and syncs state every 60 seconds.

The WebUI workflow can be started manually from GitHub Actions or automatically by the Worker when the published URL is unreachable.

## Local Use

```bash
rm -rf "$HOME/.hermes"
ln -s "$PWD/.hermes" "$HOME/.hermes"
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- \
  --skip-browser --skip-setup --non-interactive --skip-computer-use
scripts/change-model
```
Runtime files, credentials, logs, cache, binaries, and the temporary agent checkout are ignored by Git. Never commit tokens or API keys.