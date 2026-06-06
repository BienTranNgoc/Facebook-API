#!/usr/bin/env bash
set -euo pipefail

MSG=$(head -1 "$1")

[[ "$MSG" =~ ^Merge ]] && exit 0

if [[ ! "$MSG" =~ ^(feat|fix|docs|refactor|test|chore):\ .{3,} ]]; then
  echo "error: invalid commit message"
  echo "  expected: <type>: <description>"
  echo "  types: feat | fix | docs | refactor | test | chore"
  echo "  got: \"$MSG\""
  exit 1
fi
