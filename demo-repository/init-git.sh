#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# Initialize the demo-repository as a self-contained git repo with two commits:
#
#   commit 1  (tag: clean)  — clean baseline state, from .baseline/
#   commit 2  (tag: risky)  — the 8 planted risks (the files checked out here)
#
# Release Doctor analyzes the diff between these two refs. Use base_ref=clean,
# target_ref=risky in the UI (or the SHAs printed at the end).
#
# Idempotent: if a git repo with the `risky` tag already exists, it does nothing.
# After running, the working tree is left on the `risky` state so a human can
# read the planted-risk files and comments directly.
# ─────────────────────────────────────────────────────────────────────────────
set -e

REPO_DIR="${1:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
cd "$REPO_DIR"

# Deterministic identity so commits are reproducible across container restarts.
export GIT_AUTHOR_NAME="Release Doctor Demo"
export GIT_AUTHOR_EMAIL="demo@release-doctor.local"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
export GIT_AUTHOR_DATE="2024-01-01T00:00:00 +0000"
export GIT_COMMITTER_DATE="2024-01-01T00:00:00 +0000"

if [ -d .git ] && git rev-parse --verify -q risky >/dev/null 2>&1; then
  echo "demo-repository already initialized (tag 'risky' exists) — skipping."
  exit 0
fi

if [ ! -d .baseline ]; then
  echo "ERROR: .baseline/ directory not found in $REPO_DIR; cannot build clean commit." >&2
  exit 1
fi

git init -q .
git checkout -q -b master 2>/dev/null || git switch -q -c master 2>/dev/null || true

# ── Stash the risky files, lay down the clean baseline, commit as 'clean' ────
# We build the clean tree by overlaying .baseline/ onto the tracked files, then
# commit only the non-.baseline files.
TMP_RISKY="$(mktemp -d)"
# Preserve the risky versions of the files that have a clean counterpart.
( cd .baseline && find . -type f ) | while IFS= read -r rel; do
  rel="${rel#./}"
  if [ -f "$rel" ]; then
    mkdir -p "$TMP_RISKY/$(dirname "$rel")"
    cp "$rel" "$TMP_RISKY/$rel"
  fi
done

# Overlay clean baseline versions onto the working tree.
( cd .baseline && find . -type f ) | while IFS= read -r rel; do
  rel="${rel#./}"
  mkdir -p "$(dirname "$rel")"
  cp ".baseline/$rel" "$rel"
done

# Commit the clean state (exclude the .baseline helper dir from history).
echo ".baseline/" > .gitignore
git add -A
git commit -q -m "OrderFlow API — clean baseline"
git tag clean

# ── Restore the risky files, commit as 'risky' ──────────────────────────────
( cd "$TMP_RISKY" && find . -type f ) | while IFS= read -r rel; do
  rel="${rel#./}"
  cp "$TMP_RISKY/$rel" "$rel"
done
rm -rf "$TMP_RISKY"

git add -A
git commit -q -m "feat: add priority scoring, analytics tracking, refund endpoint

Introduces the OrderFlow v2 feature branch with 8 planted release risks:
missing migration, undeclared env var, breaking API change, missing auth,
missing tests, dependency CVE, stale Dockerfile, and outdated docs."
git tag risky

CLEAN_SHA="$(git rev-parse --short clean)"
RISKY_SHA="$(git rev-parse --short risky)"
echo "demo-repository initialized:"
echo "  base_ref (clean): ${CLEAN_SHA}  (tag: clean)"
echo "  target_ref (risky): ${RISKY_SHA}  (tag: risky)"
