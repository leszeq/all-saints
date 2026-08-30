#!/usr/bin/env bash

set -Eeuo pipefail

if (( $# < 3 )); then
  echo "Usage: $0 OUTPUT_FILE docker compose [options...]" >&2
  exit 64
fi

output_file=$1
shift
compose=("$@")

output_dir=$(dirname "$output_file")
temporary_file="${output_file}.tmp.$$"

cleanup() {
  rm -f -- "$temporary_file"
}
trap cleanup EXIT INT TERM

mkdir -p -- "$output_dir"

"${compose[@]}" exec -T db sh -ceu '
  pg_dump \
    --username="$POSTGRES_USER" \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-privileges \
    "$POSTGRES_DB"
' > "$temporary_file"

if [[ ! -s "$temporary_file" ]]; then
  echo "Backup archive is empty" >&2
  exit 1
fi

"${compose[@]}" exec -T db pg_restore --list < "$temporary_file" > /dev/null
mv -- "$temporary_file" "$output_file"
trap - EXIT INT TERM

echo "PostgreSQL backup created: $output_file"
