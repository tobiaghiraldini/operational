#!/usr/bin/env bash
# Create PostgreSQL role and database for Operational (django-tenants).
#
# Run on the server (requires sudo access to the postgres OS user):
#   OPERATIONAL_DB_PASSWORD='your-secret' ./deploy/postgres/create_operational_db.sh
#
# Optional environment variables:
#   OPERATIONAL_DB_NAME   default: operational
#   OPERATIONAL_DB_USER   default: tobia
#   OPERATIONAL_DB_HOST   default: localhost  (informational, for .env output)
#   OPERATIONAL_DB_PORT   default: 5432      (informational, for .env output)
#   OPERATIONAL_DB_PASSWORD  required unless GENERATE_PASSWORD=1
#   GENERATE_PASSWORD=1   generate a random password and print it
#
# Example with generated password:
#   GENERATE_PASSWORD=1 ./deploy/postgres/create_operational_db.sh

set -euo pipefail

DB_NAME="${OPERATIONAL_DB_NAME:-operational}"
DB_USER="${OPERATIONAL_DB_USER:-tobia}"
DB_HOST="${OPERATIONAL_DB_HOST:-localhost}"
DB_PORT="${OPERATIONAL_DB_PORT:-5432}"

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \?//'
  exit "${1:-0}"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage 0
fi

if ! command -v psql >/dev/null 2>&1; then
  die "psql not found; install PostgreSQL first (see deploy/postgres/install.md)"
fi

if ! sudo -u postgres psql -Atqc "SELECT 1" >/dev/null 2>&1; then
  die "cannot connect as postgres superuser (sudo -u postgres psql failed)"
fi

resolve_password() {
  if [[ -n "${OPERATIONAL_DB_PASSWORD:-}" ]]; then
    return 0
  fi
  if [[ "${GENERATE_PASSWORD:-}" == "1" ]]; then
    if command -v openssl >/dev/null 2>&1; then
      OPERATIONAL_DB_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)"
    else
      OPERATIONAL_DB_PASSWORD="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)"
    fi
    return 0
  fi
  die "set OPERATIONAL_DB_PASSWORD or GENERATE_PASSWORD=1"
}

resolve_password

# Escape single quotes for use inside PostgreSQL string literals.
escape_sql_literal() {
  printf "%s" "$1" | sed "s/'/''/g"
}

DB_PASSWORD_SQL="$(escape_sql_literal "$OPERATIONAL_DB_PASSWORD")"
DB_USER_SQL="$(escape_sql_literal "$DB_USER")"
DB_NAME_SQL="$(escape_sql_literal "$DB_NAME")"

run_as_postgres() {
  sudo -u postgres psql -v ON_ERROR_STOP=1 "$@"
}

log "Ensuring role ${DB_USER} exists"
run_as_postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER_SQL}') THEN
    CREATE ROLE "${DB_USER_SQL}" WITH LOGIN PASSWORD '${DB_PASSWORD_SQL}';
  ELSE
    ALTER ROLE "${DB_USER_SQL}" WITH LOGIN PASSWORD '${DB_PASSWORD_SQL}';
  END IF;
END
\$\$;
SQL

log "Ensuring database ${DB_NAME} exists (owner: ${DB_USER})"
DB_EXISTS="$(run_as_postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME_SQL}'")"
if [[ -z "${DB_EXISTS}" ]]; then
  run_as_postgres -c "CREATE DATABASE \"${DB_NAME_SQL}\" OWNER \"${DB_USER_SQL}\" ENCODING 'UTF8' TEMPLATE template0;"
else
  log "Database ${DB_NAME} already exists; updating owner if needed"
  run_as_postgres -c "ALTER DATABASE \"${DB_NAME_SQL}\" OWNER TO \"${DB_USER_SQL}\";"
fi

log "Granting database-level privileges to ${DB_USER}"
run_as_postgres -d postgres <<SQL
GRANT CONNECT, CREATE ON DATABASE "${DB_NAME_SQL}" TO "${DB_USER_SQL}";
SQL

log "Granting schema privileges in ${DB_NAME} (django-tenants creates tenant schemas)"
run_as_postgres -d "${DB_NAME}" <<SQL
GRANT ALL ON SCHEMA public TO "${DB_USER_SQL}";
ALTER SCHEMA public OWNER TO "${DB_USER_SQL}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${DB_USER_SQL}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${DB_USER_SQL}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO "${DB_USER_SQL}";
SQL

log "Done. Add the following to operational/.env on the server:"
cat <<ENV

# PostgreSQL (Operational / django-tenants)
DATABASE_URL=postgres://${DB_USER}:${OPERATIONAL_DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Or explicit Django settings:
# DB_NAME=${DB_NAME}
# DB_USER=${DB_USER}
# DB_PASSWORD=${OPERATIONAL_DB_PASSWORD}
# DB_HOST=${DB_HOST}
# DB_PORT=${DB_PORT}

ENV

log "Next steps:"
printf '  cd ~/Code/Ninjabit/Operational/operational\n'
printf '  python manage.py migrate\n'
printf '  python manage.py migrate_schemas\n'
