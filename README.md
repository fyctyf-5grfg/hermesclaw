# Hermes GitHub Bot

This repository runs [Hermes Agent](https://github.com/NousResearch/hermes-agent)
as a GitHub Issues bot. Opening an issue or commenting on one sends the issue
transcript to Hermes. Hermes works in the checked-out repository, and the workflow
posts its response back to the issue.

Hermes' home is deliberately kept at `.hermes/` in this repository, so sessions,
memory, skills, and configuration survive between workflow runs through git.

## Setup

1. Enable GitHub Actions and allow the workflow to write contents and issues.
2. Add `OPENAI_API_KEY` under **Settings -> Secrets and variables -> Actions**.
3. Add the repository variable `HERMES_MODEL` if you do not want `gpt-4o-mini`.
4. Add `OPENAI_BASE_URL` as a repository variable or secret when using a custom
   OpenAI-compatible service.
5. Open an issue or comment on an existing issue as an owner, member, or
   collaborator.

The bot uses `hermes -p <prompt>` by default. If the installed Hermes release uses
a different one-shot flag, set `HERMES_PROMPT_FLAG` in the workflow environment.
You can also override the executable with `HERMES_COMMAND`.

## Local Cloudflare model endpoint

The local proxy scripts use the ignored `credentials/cloudflare.txt` file and
configure Hermes to use `http://127.0.0.1:8788/v1`:

```bash
scripts/change-model
```

Set `CF_CREDENTIALS_URL` to use a different credential source, or
`CF_PROXY_PORT` to use a different local port.

## Local dry run

Create an event fixture and run:

```bash
GITHUB_EVENT_PATH=event.json HERMES_DRY_RUN=1 python3 hermes_github_bot.py
```

The dry run prints the exact prompt without contacting GitHub or starting Hermes.