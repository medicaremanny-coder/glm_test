#!/usr/bin/env bash
# Yearly CMS landscape refresh. Downloads the official ZIP and remaps
# the Plan Database extract. Does not mark 2027 data verified.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
YEAR="${1:-2026}"
VERSION="${2:-202608}"
ZIP_URL="https://www.cms.gov/files/zip/cy${YEAR}-landscape-${VERSION}.zip"
TMP_DIR="${TMPDIR:-/tmp}/cms-landscape-${YEAR}-${VERSION}"
ZIP_PATH="${TMP_DIR}/cy${YEAR}-landscape-${VERSION}.zip"

mkdir -p "$TMP_DIR"
echo "Downloading ${ZIP_URL}"
curl -fsSL -A "MedicareMannyCMSRefresh/1.0" -o "$ZIP_PATH" "$ZIP_URL"

python3 "$ROOT/scripts/map_cms_landscape.py" \
  --workbook-json "$ROOT/data/plans/workbook-plan-ids-2026-08-28.json" \
  --landscape-zip "$ZIP_PATH" \
  --out-dir "$ROOT/data/cms"

cd "$ROOT"
python3 -m unittest tests.test_cms_match -v
echo "Refresh complete. Review verification_class before any 2027 promotion."
