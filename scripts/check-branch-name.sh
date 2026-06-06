#!/usr/bin/env bash
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)
PATTERN="^(main|develop|feature\/[a-z0-9._-]+|defect\/[a-z0-9._-]+)$"

if [[ ! "$BRANCH" =~ $PATTERN ]]; then
  echo "error: branch name '$BRANCH' does not match convention"
  echo "  allowed: main | develop | feature/<name> | defect/<name>"
  exit 1
fi
