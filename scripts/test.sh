#!/usr/bin/env bash
# Single test entrypoint: shellcheck + bats + markdown link check.
# CI calls this; locally: ./scripts/test.sh  (or: make test)
# Set BATS=/path/to/bats to use a non-PATH bats binary.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BATS="${BATS:-bats}"
for tool in shellcheck "$BATS"; do
    command -v "$tool" >/dev/null 2>&1 || { echo "missing tool: $tool" >&2; exit 2; }
done

echo "== shellcheck"
shellcheck scripts/*.sh tests/check-links.sh

echo "== bats"
"$BATS" tests/

echo "== link check"
bash tests/check-links.sh

echo "all checks passed"
