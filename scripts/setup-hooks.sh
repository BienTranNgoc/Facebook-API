#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_DIR="$ROOT/.git/hooks"

if command -v pre-commit &> /dev/null; then
  cd "$ROOT"
  pre-commit install
  pre-commit install --hook-type commit-msg
  pre-commit install --hook-type pre-push
  echo "hooks installed via pre-commit"
  exit 0
fi

cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/check-commit-msg.sh" "$1"
EOF
chmod +x "$HOOKS_DIR/commit-msg"

cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/usr/bin/env bash
ROOT="$(git rev-parse --show-toplevel)"
"$ROOT/scripts/check-branch-name.sh" || exit 1
"$ROOT/scripts/check-push-target.sh" || exit 1
EOF
chmod +x "$HOOKS_DIR/pre-push"

echo "hooks installed manually (install pre-commit for full lint support)"
