#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 path/to/deck.pdf [output-directory]" >&2
  exit 2
fi

pdf_path="$1"
output_dir="${2:-rendered-slides}"

if [[ ! -f "$pdf_path" ]]; then
  echo "PDF file not found: $pdf_path" >&2
  exit 2
fi
if ! command -v gs >/dev/null 2>&1; then
  echo "Ghostscript (gs) is required to render slide previews." >&2
  exit 1
fi

mkdir -p "$output_dir"
gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=pngalpha -r120 \
  -sOutputFile="$output_dir/slide-%02d.png" "$pdf_path"

echo "Rendered slides to: $output_dir"

