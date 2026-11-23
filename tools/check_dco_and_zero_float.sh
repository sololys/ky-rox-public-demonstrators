#!/bin/sh
set -eu
BASE="${1:-HEAD~1}"
HEAD_REF="${2:-HEAD}"
for c in $(git rev-list "$BASE..$HEAD_REF"); do
    git log -n 1 --format=%B "$c" | grep -Eq '^Signed-off-by: .+ <.+@.+>$' || {
        echo "KILL: missing DCO 1.1 Signed-off-by in $c" >&2; exit 1; }
done
if git diff -U0 "$BASE..$HEAD_REF" -- '*.c' '*.h' '*.py' '*.sv' | \
   grep -Eq '^\+[^+].*(^|[^A-Za-z0-9_])(float|double|float32|float64)([^A-Za-z0-9_]|$)'; then
    echo "KILL: floating-point token in gated diff" >&2; exit 1
fi
echo "OPEN: DCO 1.1 + 0-float diff gate PASS"
