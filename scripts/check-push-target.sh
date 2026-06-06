#!/usr/bin/env bash
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" == "main" ]]; then
  echo "error: direct push to main is not allowed"
  echo "  use a pull request from develop instead"
  exit 1
fi
