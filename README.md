# Hermes GitHub Bot

This repository runs [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a GitHub Issues bot. Opening an issue or commenting on one sends the issue transcript to Hermes. Hermes works in the checked-out repository, and the workflow posts its response back to the issue.

Hermes' home is deliberately kept at `.hermes/` in this repository, so sessions, memory, skills, and configuration survive between workflow runs through git.

## Features

- **GitHub issue/PR commented on** → Hermes receives full transcript and responds with actionable changes, explanations, or summaries
- **State preserved locally** → `.hermes/` directory enables skills, memory, and session continuity across runs
- **Offset of 18-20s warm start** → Dockerless with just shell tools (no reboot container), runs on every Linux runner
- **Optional caching** → Cache fills in ~30s on first run, then subsequent runs skip the full installation (instant start)
- **Supports any LLM** → Piped through the custom Cloudflare local proxy on port 8788 (or any OpenAI-compatible service)
- **Dry-run mode** → Test workflow without touching GitHub API (no push comments)

## Quickstart

### Setup

1. Enable GitHub Actions in this repository
2. Add `OPENAI_API_KEY` under **Settings → Secrets and variables → Actions** (`cloudflare-local`)
3. (Optional) Add `HERMES_MODEL` as a repo variable; defaults to `@cf/zai-org/glm-4.7-flash`
4. (Optional) Add `HERMES_PROMPT_FLAG` if your Hermes version uses a different one-shot flag (default is `--oneshot`)
5. (Optional) Add `HERMES_COMMAND` if you want to override the `hermes` executable (default: `hermes`)
6. (Optional) Add `HERMES_TIMEOUT_SECONDS` if you need longer execution time (default: 1800s = 30m)

### Configuration

| Variable/Secret | Required? | Default | Description |
|-----------------|-----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | API key for the model provider |
| `GITHUB_TOKEN` | ✅ | Auto | GitHub token (provided automatically) |
| `HERMES_MODEL` | ❌ | `@cf/zai-org/glm-4.7-flash` | Model to use for Hermes |
| `OPENAI_BASE_URL` | ❌ | `${{ github.repository }}/actions/runner/current/externals/node20/externals/threading/` | OpenAI-compatible base URL (typically `http://127.0.0.1:8788/v1`) |
| `HERMES_COMMAND` | ❌ | `hermes` | Command to run Hermes |
| `HERMES_PROMPT_FLAG` | ❌ | `--oneshot` | Flag to pass a prompt directly to Hermes |
| `HERMES_HOME` | ❌ | `${{ github.workspace }}/.hermes` | Hermes home directory |
| `HERMES_TIMEOUT_SECONDS` | ❌ | `1800` | Maximum seconds Hermes may run |

### Local dependencies

This setup is Dockerless; everything runs on the runner:

- **curl and bash** — to install Hermes Agent
- **git** — for workspace sync and Hermes state handling
- **Python 3** (current runner) — for `hermes_github_bot.py`
- **Network access** — to download Hermes installer (`https://hermes-agent.nousresearch.com/install.sh`)

### Local Cloudflare model endpoint

The `scripts/cf-proxy.py` script starts a local OpenAI-compatible proxy on port 8788:

```bash
# Run locally (requires curl & Python)
python3 scripts/cf-proxy.py

# Or modify scripts/change-model to use a different port or credentials
CF_PROXY_PORT=8080 python3 scripts/cf-proxy.py
```

**Configuration options:**

- `CF_CREDENTIALS_URL` — path to a credentials file (defaults to `credentials/cloudflare.txt`)
- `CF_PROXY_PORT` — listen port (defaults to `8788`)

### Local dry run

Create an event fixture and test without contacting GitHub:

```bash
GITHUB_EVENT_PATH=event.json HERMES_DRY_RUN=1 python3 hermes_github_bot.py
```

This prints the exact prompt that Hermes would see, without running Hermes or sending a GitHub comment.

## How Hermes processes GitHub issues

When you open an issue or comment, Hermes receives:

1. **Issue title** and **body**
2. **All historical comments** (ordered chronologically)
3. **Event name** (e.g., `issue_comment`, `issues`)
4. **Repository context** (via `GITHUB_TOKEN`)

Hermes uses its skills and memory to address requests, write code, review PRs, summarize docs, or perform other coding tasks. It works directly within the repository and may:

- Edit files, run tests, or lint commits
- Generate new tools, skills, or shell scripts
- Ask clarifying questions (via tools or this issue)
- Respond briefly with a summary and next steps

All responses are posted back to the GitHub issue as comments.

## Updating the workflow (if you maintain this repo)

If you extend or fork this bot, remember a few invariants:

- **State lives in `.hermes/`** — persist skills, memory, and config across runs
- **Link `~/.hermes` to repo** — the workflow updates the symlink: `ln -s ${{ github.workspace }}/.hermes $HOME/.hermes`
- **Cleanup `[bot]` after Hermes completes** — post-install step runs `rm -rf ${{ github.workspace }}/.hermes/hermes-agent` before committing state
- **Cache optional, but helpful** — skip reinstall if Prometheus metrics show `hermes_agent_state_setup_duration_seconds` remains low after cache restore
- **Hermes target is the repo root** — Hermes' workspace (`--in`) and the bot's `cwd` are set to `${{ github.workspace }}`

## Troubleshooting

### "Missing Authentication header" (HTTP 401)

- Verify `GITHUB_TOKEN` is set in the workflow
- Ensure actions/checkout step ran before Hermes runs (workflow order)
- Check runner service permissions: `write` for issues and contents

### "No repository is currently checked out"

- The workflow may be running an orphan branch without a commit
- Verify the event path includes `repository` and `shoot`/`fork` path resolves correctly
- Test locally via `GITHUB_EVENT_PATH=` in dry run to see what the bot receives

### Hermes installer is slow or hangs

- Hermes installation is cached (first run ~18–20s; subsequent runs ~0s if cache present)
- Verify network connectivity to `hermes-agent.nousresearch.com/install.sh`
- Check if Prometheus metrics include `hermes_agent_state_snapshot_hash` (validates cache key)

### Cloudflare proxy is not reachable

- `scripts/cf-proxy.py` must be running on port 8788
- Verify `OPENAI_BASE_URL` is set to `http://127.0.0.1:8788/v1`
- Check `cf-proxy.py` logs: spawn logs in `/tmp/cf-proxy.py.log`
- If using a different proxy, adjust the health check line (actor line 62–65 in `.github/workflows/hermes-bot.yml`)

### Hermes exits with status X

- Check GitHub Actions job logs after the Hermes step
- Hermes may throw an error (timeout, model fault, permission denied, file conflict)
- Trigger on safe copy-and-paste failure with a unique identifier to avoid downstream build flames

### State stays stale between runs

- Ensure `.hermes/` is in `.gitignore` (this repo does, but forks should mirror pattern)
- If manually moving state, delete and relink: `rm -rf $HOME/.hermes && ln -s ${{ github.workspace }}/.hermes $HOME/.hermes`
- Check that your Hermes version uses the same prompt flag (e.g., `--oneshot` vs `-p`)

### Hermes produces empty response

- Check Hermes tool output (stdout) for stderr
- Verify that the workspace is not empty or locked (e.g., second run or concurrent checkout)
- In dry-run mode, ensure `GITHUB_EVENT_PATH` points to a valid issue event

## Alternatives or extensions

This is a minimal Hermes wrapper. For a more feature-rich setup:

- **SSH or web-ready Hermes** — build a gateway between Hermes and a hosted infrastructure gateway
- **Repository-specific skills** — override `.hermes/.skills_prompt_snapshot.json` to skip workspace awareness
- **Routing by org/team** — gate Hermes only on OWNER/MEMBER/COLLABORATOR runs
- **Remote Hermes executable** — set `HERMES_COMMAND` to a remote runner (SSH/sftp/rsync) if runner resources are constrained

## References

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — main project
- [Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/) — complete docs, API, and features
- [Hermes Agent llms.txt index](https://hermes-agent.nousresearch.com/docs/llms.txt) — searchable overview of all Hermes capabilities
- [GitHub Actions checkout reference](https://github.com/actions/checkout) — checkout v4 options and token handling