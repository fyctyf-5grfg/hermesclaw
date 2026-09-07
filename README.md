# Hermes GitHub Bot

This repository runs [Hermes Agent](https://github.com/NousResearch/hermes-agent) as a GitHub Issues bot. Opening an issue or commenting on one sends the issue transcript to Hermes. Hermes works in the checked-out repository, and the workflow posts its response back to the issue.

Hermes' home is deliberately kept at `.hermes/` in this repository, so sessions, memory, skills, and configuration survive between workflow runs through git.

## Features


## Quickstart

### Setup

1. Enable GitHub Actions in this repository
2. Add `OPENAI_API_KEY` under **Settings → Secrets and variables → Actions** (`cloudflare-local`)
3. Add the `TOKEN` repository secret with Contents, Actions, Packages, and Workflows write access
4. (Optional) Add `HERMES_MODEL` as a repo variable; defaults to `@cf/zai-org/glm-4.7-flash`
5. (Optional) Add `HERMES_PROMPT_FLAG` if your Hermes version uses a different one-shot flag (default is `--oneshot`)
6. (Optional) Add `HERMES_COMMAND` if you want to override the `hermes` executable (default: `hermes`)
7. (Optional) Add `HERMES_TIMEOUT_SECONDS` if you need longer execution time (default: 1800s = 30m)

### Configuration

| Variable/Secret | Required? | Default | Description |
|-----------------|-----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | API key for the model provider |
| `GITHUB_TOKEN` | ✅ | Auto | GitHub token (provided automatically) |
| `TOKEN` | ✅ | — | Repository token used by workflows for GitHub writes and workflow updates |
| `HERMES_MODEL` | ❌ | `@cf/zai-org/glm-4.7-flash` | Model to use for Hermes |
| `OPENAI_BASE_URL` | ❌ | `${{ github.repository }}/actions/runner/current/externals/node20/externals/threading/` | OpenAI-compatible base URL (typically `http://127.0.0.1:8788/v1`) |
| `HERMES_COMMAND` | ❌ | `hermes` | Command to run Hermes |
| `HERMES_PROMPT_FLAG` | ❌ | `--oneshot` | Flag to pass a prompt directly to Hermes |
| `HERMES_HOME` | ❌ | `${{ github.workspace }}/.hermes` | Hermes home directory |
| `HERMES_TIMEOUT_SECONDS` | ❌ | `1800` | Maximum seconds Hermes may run |

### Local dependencies

This setup is Dockerless; everything runs on the runner:


### Local Cloudflare model endpoint

The `scripts/cf-proxy.py` script starts a local OpenAI-compatible proxy on port 8788:

```bash
# Run locally (requires curl & Python)
python3 scripts/cf-proxy.py

# Or modify scripts/change-model to use a different port or credentials
CF_PROXY_PORT=8080 python3 scripts/cf-proxy.py
```

**Configuration options:**


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


All responses are posted back to the GitHub issue as comments.

## Updating the workflow (if you maintain this repo)

If you extend or fork this bot, remember a few invariants:


## Troubleshooting

### "Missing Authentication header" (HTTP 401)


### "No repository is currently checked out"


### Hermes installer is slow or hangs


### Cloudflare proxy is not reachable


### Hermes exits with status X


### State stays stale between runs


### Hermes produces empty response


## Alternatives or extensions

This is a minimal Hermes wrapper. For a more feature-rich setup:


## References
