#!/usr/bin/env bash
# Verify every relative link/image in README.md and docs/**/*.md points at an
# existing file or directory. External (http/https/mailto) links are skipped.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

mapfile -t files < <(ls README.md 2>/dev/null; find docs -name '*.md' -type f | sort)

fail=0
checked=0
for file in "${files[@]}"; do
    dir="$(dirname "$file")"
    # Markdown links/images: [text](target) and HTML src="/href=" attributes.
    while IFS= read -r target; do
        [ -z "$target" ] && continue
        case "$target" in
            http://*|https://*|mailto:*|\#*) continue ;;
        esac
        target="${target%%#*}"   # strip fragment
        target="${target%%\?*}"  # strip query
        [ -z "$target" ] && continue
        checked=$((checked + 1))
        if [ ! -e "$dir/$target" ]; then
            echo "BROKEN: $file -> $target"
            fail=1
        fi
    done < <(grep -oE '\]\([^)[:space:]]+\)|(src|href)="[^"]+"' "$file" \
             | sed -E 's/^\]\(//; s/\)$//; s/^(src|href)="//; s/"$//')
done

echo "link check: ${#files[@]} files, $checked relative links, $( [ "$fail" -eq 0 ] && echo OK || echo FAILED )"
exit "$fail"
