#!/usr/bin/env bash
# Bump KRV assistant embed cache-bust version (?v=...) in one shot.
#
# Updates:
#   - 6 service landings (index.html)
#   - WP hub theme: inc/krv-assistant.php
#
# Usage:
#   ./scripts/bump-widget-version.sh 20260730r
#   ./scripts/bump-widget-version.sh 20260730r --dry-run
#
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bump-widget-version.sh <new_version> [--dry-run]

Bump KRV assistant widget version (?v=...) everywhere it is hardcoded.

Targets:
  /var/www/{ai-ready,bots,direct,landing,vps,wordpress}.krivoshein.site/htdocs/index.html
  /var/www/krivoshein.site/htdocs/wp-content/themes/drslon-blog-theme/inc/krv-assistant.php

Examples:
  bump-widget-version.sh 20260730r
  bump-widget-version.sh 20260730r --dry-run

Notes:
  - Replaces only krv-assistant.js?v=... (not theme-i18n / logo cache-busts).
  - Exit 1 if any target is missing or has no embed line.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
  [[ $# -ge 1 && ( "${1}" == "-h" || "${1}" == "--help" ) ]] && exit 0
  exit 1
fi

NEW_VERSION="${1}"
DRY_RUN=0
if [[ "${2:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ -n "${2:-}" ]]; then
  echo "Unknown option: $2" >&2
  usage >&2
  exit 1
fi

if [[ ! "$NEW_VERSION" =~ ^[0-9A-Za-z._-]+$ ]]; then
  echo "Invalid version: '$NEW_VERSION' (use letters, digits, . _ - only)" >&2
  exit 1
fi

LANDINGS=(
  ai-ready
  bots
  direct
  landing
  vps
  wordpress
)

FILES=()
for site in "${LANDINGS[@]}"; do
  FILES+=("/var/www/${site}.krivoshein.site/htdocs/index.html")
done
FILES+=("/var/www/krivoshein.site/htdocs/wp-content/themes/drslon-blog-theme/inc/krv-assistant.php")

# Match only the assistant embed, not other ?v= cache-busts.
PATTERN='krv-assistant\.js\?v=[^"'\''&[:space:]]*'
EXTRACT_RE='krv-assistant\.js\?v=\K[^"'\''&[:space:]]+'

updated=0
unchanged=0
failed=0

echo "New version: ${NEW_VERSION}"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Mode:       dry-run (no writes)"
else
  echo "Mode:       apply"
fi
echo "----"

for f in "${FILES[@]}"; do
  label="${f}"
  if [[ ! -f "$f" ]]; then
    echo "MISS  $label  (file not found)"
    failed=$((failed + 1))
    continue
  fi

  old="$(grep -oP "$EXTRACT_RE" "$f" | head -n1 || true)"
  if [[ -z "$old" ]]; then
    echo "MISS  $label  (no krv-assistant.js?v=… found)"
    failed=$((failed + 1))
    continue
  fi

  if [[ "$old" == "$NEW_VERSION" ]]; then
    echo "OK    $label  already v=${old}"
    unchanged=$((unchanged + 1))
    continue
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "PLAN  $label  ${old} → ${NEW_VERSION}"
    updated=$((updated + 1))
    continue
  fi

  # Portable in-place replace (GNU sed on this host).
  sed -i -E "s|krv-assistant\\.js\\?v=[^\"'&[:space:]]+|krv-assistant.js?v=${NEW_VERSION}|g" "$f"

  new="$(grep -oP "$EXTRACT_RE" "$f" | head -n1 || true)"
  if [[ "$new" == "$NEW_VERSION" ]]; then
    echo "DONE  $label  ${old} → ${new}"
    updated=$((updated + 1))
  else
    echo "FAIL  $label  expected ${NEW_VERSION}, got '${new:-empty}'"
    failed=$((failed + 1))
  fi
done

echo "----"
echo "Summary: updated=${updated} unchanged=${unchanged} failed=${failed} total=${#FILES[@]}"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi

if [[ "$DRY_RUN" -eq 0 && "$updated" -gt 0 ]]; then
  echo
  echo "Next (theme git, if PHP changed):"
  echo "  cd /var/www/krivoshein.site/htdocs/wp-content/themes/drslon-blog-theme"
  echo "  git add inc/krv-assistant.php && git commit -m 'chore: bump KRV assistant embed to v=${NEW_VERSION}' && git push"
fi

exit 0
