#!/usr/bin/env bash
# Create /var/www/operational static + media dirs with nginx-readable permissions.
#
# Run on the server (requires sudo):
#   ./deploy/nginx/prepare_www_dirs.sh
#
# Optional environment variables:
#   OPERATIONAL_WWW_ROOT=/var/www/operational
#   OPERATIONAL_UNIX_USER=Tobj   (default: current user)
#   OPERATIONAL_UNIX_GROUP=www-data

set -euo pipefail

WWW_ROOT="${OPERATIONAL_WWW_ROOT:-/var/www/operational}"
STATIC_DIR="${WWW_ROOT}/static"
MEDIA_DIR="${WWW_ROOT}/media"
DEPLOY_USER="${OPERATIONAL_UNIX_USER:-${USER:-Tobj}}"
WEB_GROUP="${OPERATIONAL_UNIX_GROUP:-www-data}"

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  exit 0
fi

if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  die "user not found: $DEPLOY_USER (set OPERATIONAL_UNIX_USER)"
fi

if ! getent group "$WEB_GROUP" >/dev/null 2>&1; then
  die "group not found: $WEB_GROUP (install nginx first or set OPERATIONAL_UNIX_GROUP)"
fi

log "Creating directories under ${WWW_ROOT}"
sudo mkdir -p "$STATIC_DIR" "$MEDIA_DIR"

log "Setting ownership ${DEPLOY_USER}:${WEB_GROUP}"
sudo chown -R "${DEPLOY_USER}:${WEB_GROUP}" "$WWW_ROOT"

log "Setting permissions (dirs 775, files 664 when present)"
sudo find "$WWW_ROOT" -type d -exec chmod 775 {} +
if [[ -n "$(sudo find "$WWW_ROOT" -type f -print -quit 2>/dev/null)" ]]; then
  sudo find "$WWW_ROOT" -type f -exec chmod 664 {} +
fi

log "Verifying nginx can read static directory"
if sudo -u "$WEB_GROUP" test -x "$WWW_ROOT" && sudo -u "$WEB_GROUP" test -x "$STATIC_DIR"; then
  log "nginx group can traverse ${WWW_ROOT} and ${STATIC_DIR}"
else
  die "nginx group (${WEB_GROUP}) cannot traverse ${STATIC_DIR}; check permissions"
fi

log "Done. Add or update these lines in operational/.env:"
cat <<ENV

STATIC_ROOT=${STATIC_DIR}
MEDIA_ROOT=${MEDIA_DIR}

ENV

log "Next steps:"
printf '  python manage.py collectstatic --noinput\n'
printf '  sudo nginx -t && sudo systemctl reload nginx\n'
printf '  curl -I https://operational.cloud/static/css/home.css\n'
