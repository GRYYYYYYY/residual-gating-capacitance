#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
case "${1:-main}" in
  main|extended) papers=("${1:-main}") ;;
  all) papers=(main extended) ;;
  *) echo "Usage: bash build.sh [main|extended|all]" >&2; exit 2 ;;
esac
for paper in "${papers[@]}"; do
  latexmk -pdf -interaction=nonstopmode -halt-on-error -recorder "$paper.tex"
done
