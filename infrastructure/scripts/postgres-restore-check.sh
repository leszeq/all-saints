#!/usr/bin/env bash

set -Eeuo pipefail

if (( $# < 4 )); then
  echo "Usage: $0 BACKUP_FILE RESTORE_DB docker compose [options...]" >&2
  exit 64
fi

backup_file=$1
restore_database=$2
shift 2
compose=("$@")

if [[ ! -f "$backup_file" || ! -s "$backup_file" ]]; then
  echo "Backup file does not exist or is empty: $backup_file" >&2
  exit 66
fi

if [[ ! "$restore_database" =~ ^all_saints_restore_test_[0-9]{14}$ ]]; then
  echo "Refusing unsafe restore database name: $restore_database" >&2
  exit 64
fi

created=false

drop_test_database() {
  "${compose[@]}" exec -T -e "RESTORE_DB=$restore_database" db sh -ceu '
    dropdb --if-exists --username="$POSTGRES_USER" "$RESTORE_DB"
  '
}

cleanup() {
  if [[ "$created" == true ]]; then
    drop_test_database > /dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

"${compose[@]}" exec -T db pg_restore --list < "$backup_file" > /dev/null

"${compose[@]}" exec -T -e "RESTORE_DB=$restore_database" db sh -ceu '
  createdb --username="$POSTGRES_USER" "$RESTORE_DB"
'
created=true

"${compose[@]}" exec -T -e "RESTORE_DB=$restore_database" db sh -ceu '
  pg_restore \
    --username="$POSTGRES_USER" \
    --dbname="$RESTORE_DB" \
    --exit-on-error \
    --single-transaction \
    --no-owner \
    --no-privileges
' < "$backup_file"

table_count=$(
  "${compose[@]}" exec -T -e "RESTORE_DB=$restore_database" db sh -ceu '
    psql --username="$POSTGRES_USER" --dbname="$RESTORE_DB" \
      --tuples-only --no-align \
      --command="SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';"
  ' | tr -d '[:space:]'
)

if [[ ! "$table_count" =~ ^[1-9][0-9]*$ ]]; then
  echo "Restore check found no public tables" >&2
  exit 1
fi

alembic_version=$(
  "${compose[@]}" exec -T -e "RESTORE_DB=$restore_database" db sh -ceu '
    psql --username="$POSTGRES_USER" --dbname="$RESTORE_DB" \
      --tuples-only --no-align \
      --command="SELECT version_num FROM alembic_version;"
  ' | tr -d '[:space:]'
)

if [[ -z "$alembic_version" ]]; then
  echo "Restore check found no Alembic version" >&2
  exit 1
fi

drop_test_database
created=false
trap - EXIT INT TERM

echo "Restore check passed: $table_count tables, Alembic $alembic_version"
