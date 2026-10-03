#!/usr/bin/env bash
# ==============================================================================
# KY-ROX Public Demonstrators // Automatic Wiki Deployment Script
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIKI_DIR="${SCRIPT_DIR}"
TEMP_WIKI="/tmp/ky-rox-wiki-sync"

WIKI_REMOTE="git@github.com:sololys/ky-rox-public-demonstrators.wiki.git"

echo "==> Synkroniserer KY-ROX Wiki til ${WIKI_REMOTE}..."

rm -rf "${TEMP_WIKI}"
git clone "${WIKI_REMOTE}" "${TEMP_WIKI}"

echo "==> Kopierer alle wiki-dokumenter..."
cp "${WIKI_DIR}"/*.md "${TEMP_WIKI}/"

cd "${TEMP_WIKI}"
git add .
if git diff --staged --quiet; then
    echo "==> Ingen endringer å committe i wikien."
else
    git commit -m "docs(wiki): synchronize authoritative documentation suite (Home, Brahman-1, Attestation, Boundary, Microtests)"
    git push origin HEAD
    echo "==> ✅ Fullført! Wiki er nå 100% oppdatert på GitHub."
fi

rm -rf "${TEMP_WIKI}"
