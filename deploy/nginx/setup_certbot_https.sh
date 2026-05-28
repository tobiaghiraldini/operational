#!/usr/bin/env bash
# Install Certbot (if needed) and enable HTTPS for operational.cloud on Nginx.
#
# Usage:
#   LETSENCRYPT_EMAIL=admin@operational.cloud ./deploy/nginx/setup_certbot_https.sh
#
# Optional environment variables:
#   DOMAIN=operational.cloud
#   NGINX_SITE_CONF=/etc/nginx/sites-available/operational.conf
#   NGINX_SITE_ENABLED=/etc/nginx/sites-enabled/operational.conf
#   LETSENCRYPT_EMAIL=admin@operational.cloud
#   LETSENCRYPT_NO_EMAIL=1   # only if you really do not want to provide an email

set -euo pipefail

DOMAIN="${DOMAIN:-operational.cloud}"
NGINX_SITE_CONF="${NGINX_SITE_CONF:-/etc/nginx/sites-available/operational.cloud}"
NGINX_SITE_ENABLED="${NGINX_SITE_ENABLED:-/etc/nginx/sites-enabled/operational.cloud}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
LETSENCRYPT_NO_EMAIL="${LETSENCRYPT_NO_EMAIL:-0}"

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

run_sudo() {
  sudo "$@"
}

ensure_certbot_installed() {
  if command -v certbot >/dev/null 2>&1; then
    log "Certbot already installed: $(certbot --version)"
    return 0
  fi

  log "Certbot not found. Trying apt installation (python3-certbot-nginx)."
  if command -v apt-get >/dev/null 2>&1; then
    run_sudo apt-get update
    run_sudo apt-get install -y certbot python3-certbot-nginx
  fi

  if command -v certbot >/dev/null 2>&1; then
    log "Certbot installed via apt."
    return 0
  fi

  log "Apt install unavailable/failed. Trying snap fallback."
  if ! command -v snap >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      run_sudo apt-get install -y snapd
    else
      die "snap is not available and apt-get is missing; install certbot manually"
    fi
  fi

  run_sudo snap install core
  run_sudo snap refresh core
  run_sudo snap install --classic certbot
  if [[ ! -e /usr/bin/certbot ]]; then
    run_sudo ln -s /snap/bin/certbot /usr/bin/certbot
  fi

  command -v certbot >/dev/null 2>&1 || die "Certbot installation failed"
  log "Certbot installed via snap."
}

ensure_nginx_ready() {
  command -v nginx >/dev/null 2>&1 || die "nginx not found; install nginx first"
  [[ -f "$NGINX_SITE_CONF" ]] || die "nginx config not found: $NGINX_SITE_CONF"

  if [[ ! -e "$NGINX_SITE_ENABLED" ]]; then
    log "Enabling nginx site: $NGINX_SITE_ENABLED -> $NGINX_SITE_CONF"
    run_sudo ln -s "$NGINX_SITE_CONF" "$NGINX_SITE_ENABLED"
  fi

  log "Validating nginx config"
  run_sudo nginx -t
  run_sudo systemctl reload nginx
}

request_certificate() {
  if [[ "$LETSENCRYPT_NO_EMAIL" == "1" ]]; then
    log "Requesting certificate without email (not recommended)."
    run_sudo certbot --nginx \
      --non-interactive \
      --agree-tos \
      --register-unsafely-without-email \
      --redirect \
      --keep-until-expiring \
      -d "$DOMAIN"
    return 0
  fi

  [[ -n "$LETSENCRYPT_EMAIL" ]] || die "set LETSENCRYPT_EMAIL (or LETSENCRYPT_NO_EMAIL=1)"

  log "Requesting certificate for $DOMAIN with email $LETSENCRYPT_EMAIL"
  run_sudo certbot --nginx \
    --non-interactive \
    --agree-tos \
    --email "$LETSENCRYPT_EMAIL" \
    --redirect \
    --keep-until-expiring \
    -d "$DOMAIN"
}

show_renewal_status() {
  log "Checking renewal with dry-run"
  run_sudo certbot renew --dry-run || log "Dry-run renewal failed; check certbot/nginx logs"
}

main() {
  log "Preparing HTTPS for domain: $DOMAIN"
  ensure_certbot_installed
  ensure_nginx_ready
  request_certificate
  show_renewal_status
  log "Done. HTTPS should now be active for $DOMAIN"
}

main "$@"
