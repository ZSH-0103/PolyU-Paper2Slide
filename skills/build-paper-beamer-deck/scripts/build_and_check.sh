#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 path/to/deck.tex" >&2
  exit 2
fi

tex_path="$1"
if [[ ! -f "$tex_path" ]]; then
  echo "TeX file not found: $tex_path" >&2
  exit 2
fi

deck_dir="$(cd "$(dirname "$tex_path")" && pwd)"
tex_name="$(basename "$tex_path")"
log_name="${tex_name%.tex}.log"

(
  cd "$deck_dir"
  latexmk -xelatex -interaction=nonstopmode -halt-on-error "$tex_name"
)

log_path="$deck_dir/$log_name"
if [[ ! -f "$log_path" ]]; then
  echo "Expected log file not found: $log_path" >&2
  exit 1
fi

if command -v rg >/dev/null 2>&1; then
  pattern='Overfull|LaTeX Error|Package .* Error'
  if rg -n "$pattern" "$log_path"; then
    echo "Build completed with layout or LaTeX problems." >&2
    exit 1
  fi

  if rg -n 'Underfull' "$log_path"; then
    echo "Underfull boxes found: inspect the rendered slides before delivery." >&2
  fi
else
  if grep -En 'Overfull|LaTeX Error|Package .* Error' "$log_path"; then
    echo "Build completed with layout or LaTeX problems." >&2
    exit 1
  fi
fi

echo "Build and source checks passed: ${tex_path%.tex}.pdf"

