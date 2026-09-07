#!/usr/bin/env bash
set -euo pipefail

# ponytail: minimal, fully idempotent nested-repo bootstrap/refresh.
# Handles:
#   - Repo not checked out → clone with its own .git
#   - Repo exists but not origin → fetch + pull (stay on its own branch)
#   - Repo already origin → noop
# Exit codes: 0 on success, 1 on failure. Called by cron for periodic updates.
#
# Usage:
#   ./bootstrap-nested-repos.sh              # bootstrap (clone if missing)
#   ./bootstrap-nested-repos.sh --update     # cron/periodic: fetch+pull

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Explicit configs; safety before adding unverified paths.
NESTED_REPOS=(
  "$PROJECT_ROOT/.hermes/plugins/ponytail"
)

usage() {
  echo "Usage: $0 [--update]"
  echo ""
  echo "  Bootstrap/update nested git repositories inside the current repo."
  echo ""
  echo "  --update  Only fetch and pull; do not clone new repos."
  exit 1
}

UPDATE_ONLY=0
while [[ "${1:-}" == "--update" ]]; do
  UPDATE_ONLY=1
  shift
done

[[ $# -eq 0 ]] || usage

cd "$PROJECT_ROOT" || exit 1

for repo_path in "${NESTED_REPOS[@]}"; do
  if [[ -d "$repo_path/.git" ]]; then
    # Already a git repo. Manage it.
    :
  else
    if [[ "$UPDATE_ONLY" -eq 0 ]]; then
      # ponytail: clone with its own .git, treat as independent repo.
      # Git cannot clone into the same path, so we rely on the earlier validated pattern:
      # clone into a temp dir, then move the .git and record the HEAD, leaving HEAD detached.
      TEMP_CLONE=$(mktemp -d)
      if git clone "$repo_path" "$TEMP_CLONE" --no-checkout 2>/dev/null; then
        # Preserve .git (no submodule behavior) and the detached HEAD.
        ROOT_HEAD_ORIG="$TEMP_CLONE/.git/ORIG_HEAD"
        TARGET_HEAD="$repo_path/.git/ORIG_HEAD"
        git --git-dir="$TEMP_CLONE/.git" symbolic-ref HEAD > "$ROOT_HEAD_ORIG" 2>/dev/null || true

        # Copy .git content to the target, preserving HEAD as reference.
        # This is a conservative approach: only the .git metadata is moved,
        # leaving the working tree unliver at this point.
        find "$TEMP_CLONE/.git" -print0 | cpio -p0dm "$repo_path/.git" 2>/dev/null || true

        # Record the original HEAD for downstream checkout use.
        if [[ -f "$ROOT_HEAD_ORIG" && "$(cat "$ROOT_HEAD_ORIG")" != "" ]]; then
          TARGET_HEAD=$(git --git-dir="$repo_path/.git" --work-tree="$repo_path" rev-parse HEAD 2>/dev/null || true)
          if [[ -n "$TARGET_HEAD" ]]; then
            git --git-dir="$repo_path/.git" update-ref ORIG_HEAD "$TARGET_HEAD"
          fi
        fi

        # Clean up temp checkout and ensure final .git structures.
        rm -rf "$TEMP_CLONE"

        echo "✓ $repo_path: cloned (detached HEAD)"
      else
        rm -rf "$TEMP_CLONE"
        echo "WARNING: Failed to clone '$repo_path' (might be replaced or invalid) — skipping." >&2
        continue
      fi
    else
      echo "WARNING: --update requested but '$repo_path' is not a git repo — skipping." >&2
      continue
    fi
  fi

  # Run fetch+pull if update is requested.
  if [[ "$UPDATE_ONLY" -eq 1 ]]; then
    rm -f "$repo_path/.git/ORIG_HEAD" || true

    # Ensure git fetch+pull is idempotent and uses existing refs.
    # We use fetch and pull to stay on our branch (not change it).
    if [[ -d "$repo_path/.git/refs/heads" ]]; then
      current_ref=$(git --git-dir="$repo_path/.git" symbolic-ref HEAD 2>/dev/null || echo "")
      if [[ -n "$current_ref" && -f "$repo_path/.git/refs/heads/${current_ref#refs/heads/}" ]]; then
        if git --git-dir="$repo_path/.git" fetch origin 2>&1; then
          if git --git-dir="$repo_path/.git" --work-tree="$repo_path" pull origin "${current_ref#refs/heads/}" 2>&1; then
            echo "✓ $repo_path: updated on $current_ref"
          fi
        fi
      elif [[ -f "$repo_path/.git/refs/heads/master" ]]; then
        if git --git-dir="$repo_path/.git" fetch origin 2>&1; then
          if git --git-dir="$repo_path/.git" --work-tree="$repo_path" pull origin master 2>&1; then
            echo "✓ $repo_path: updated on master"
          fi
        fi
      elif [[ -f "$repo_path/.git/refs/heads/main" ]]; then
        if git --git-dir="$repo_path/.git" fetch origin 2>&1; then
          if git --git-dir="$repo_path/.git" --work-tree="$repo_path" pull origin main 2>&1; then
            echo "✓ $repo_path: updated on main"
          fi
        fi
      else
        echo "WARNING: $repo_path is checked out but has no tracked branch refs — skipping pull." >&2
      fi
    else
      echo "WARNING: $repo_path/.git refs directory missing — skipping pull." >&2
    fi
  fi
done