#!/usr/bin/env python3
"""Run Hermes for a GitHub issue event and publish the response."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
HERMES_HOME = Path(os.environ.get("HERMES_HOME", ROOT / ".hermes"))
EVENT_PATH = Path(os.environ.get("GITHUB_EVENT_PATH", "event.json"))
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def github(method: str, path: str, payload: dict | None = None) -> dict | list:
    request = Request(f"{API}{path}", method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("Authorization", f"Bearer {TOKEN}")
    if payload is not None:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(payload).encode()
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def event_context(event: dict) -> tuple[str, int, str, str, list[dict]]:
    repository = event["repository"]["full_name"]
    issue = event.get("issue", event.get("pull_request"))
    if issue is None:
        raise ValueError("This event does not contain an issue or pull request")
    number = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body") or ""
    comments = github("GET", f"/repos/{repository}/issues/{number}/comments")
    return repository, number, title, body, comments


def build_prompt(event_name: str, title: str, body: str, comments: list[dict]) -> str:
    transcript = [f"Issue title: {title}", f"Issue body:\n{body}"]
    for comment in comments:
        author = comment.get("user", {}).get("login", "unknown")
        transcript.append(f"{author} commented:\n{comment.get('body') or ''}")
    transcript.append(
        "Act as the repository's Hermes coding agent. Work directly in the checked-out repository. "
        "Inspect relevant files, implement the request when appropriate, and explain the result briefly. "
        "Do not reveal secrets or claim changes you did not make."
    )
    return f"GitHub event: {event_name}\n\n" + "\n\n---\n\n".join(transcript)


def run_hermes(prompt: str) -> str:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    command = shlex.split(os.environ.get("HERMES_COMMAND", "hermes"))
    prompt_flag = os.environ.get("HERMES_PROMPT_FLAG", "-p")
    command.extend([prompt_flag, prompt])
    environment = os.environ.copy()
    environment["HERMES_HOME"] = str(HERMES_HOME)
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=int(os.environ.get("HERMES_TIMEOUT_SECONDS", "1800")),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Hermes exited with status {result.returncode}: {detail[-4000:]}")
    response = result.stdout.strip()
    if not response:
        raise RuntimeError("Hermes returned an empty response")
    return response


def post_comment(repository: str, number: int, response: str) -> None:
    limit = 60000
    chunks = [response[i : i + limit] for i in range(0, len(response), limit)]
    for chunk in chunks:
        github("POST", f"/repos/{repository}/issues/{number}/comments", {"body": chunk})


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "issues")
    event = json.loads(EVENT_PATH.read_text())
    if os.environ.get("HERMES_DRY_RUN") == "1":
        issue = event.get("issue", event.get("pull_request"))
        if issue is None:
            print("This event does not contain an issue or pull request", file=sys.stderr)
            return 1
        repository = event["repository"]["full_name"]
        number = issue["number"]
        title = issue.get("title", "")
        body = issue.get("body") or ""
        comments = []
    else:
        repository, number, title, body, comments = event_context(event)
    prompt = build_prompt(event_name, title, body, comments)
    if os.environ.get("HERMES_DRY_RUN") == "1":
        print(prompt)
        return 0
    try:
        response = run_hermes(prompt)
        post_comment(repository, number, response)
        return 0
    except (HTTPError, OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())