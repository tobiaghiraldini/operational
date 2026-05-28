#!/usr/bin/env bash
# Install Certbot (if needed) and issue certificates for Operational.
#
# Usage:
#   LETSENCRYPT_EMAIL=admin@operational.cloud ./deploy/nginx/setup_certbot_https.sh
#
# Optional environment variables:
#   BASE_DOMAIN=operational.cloud
#   CERT_MODE=apex      # default: HTTP challenge via nginx, cert for base domain only
#   CERT_MODE=wildcard  # DNS challenge, cert for base + *.base
#   NGINX_SITE_CONF=/etc/nginx/sites-available/operational.conf
#   NGINX_SITE_ENABLED=/etc/nginx/sites-enabled/operational.conf
#   LETSENCRYPT_EMAIL=admin@operational.cloud
#   LETSENCRYPT_NO_EMAIL=1   # only if you really do not want to provide an email

set -euo pipefail

BASE_DOMAIN="${BASE_DOMAIN:-operational.cloud}"
CERT_MODE="${CERT_MODE:-apex}"
NGINX_SITE_CONF="${NGINX_SITE_CONF:-/etc/nginx/sites-available/operational.conf}"
NGINX_SITE_ENABLED="${NGINX_SITE_ENABLED:-/etc/nginx/sites-enabled/operational.conf}"
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

request_certificate_apex() {
  if [[ "$LETSENCRYPT_NO_EMAIL" == "1" ]]; then
    log "Requesting apex certificate without email (not recommended)."
    run_sudo certbot --nginx \
      --non-interactive \
      --agree-tos \
      --register-unsafely-without-email \
      --redirect \
      --keep-until-expiring \
      -d "$BASE_DOMAIN"
    return 0
  fi

  [[ -n "$LETSENCRYPT_EMAIL" ]] || die "set LETSENCRYPT_EMAIL (or LETSENCRYPT_NO_EMAIL=1)"

  log "Requesting apex certificate for $BASE_DOMAIN with email $LETSENCRYPT_EMAIL"
  run_sudo certbot --nginx \
    --non-interactive \
    --agree-tos \
    --email "$LETSENCRYPT_EMAIL" \
    --redirect \
    --keep-until-expiring \
    -d "$BASE_DOMAIN"
}

request_certificate_wildcard() {
  log "Wildcard mode selected for *.${BASE_DOMAIN}"
  log "Wildcard certificates require DNS challenge (HTTP challenge is not allowed)."
  log "You will be prompted to add TXT records in DNS for _acme-challenge.${BASE_DOMAIN}."

  if [[ "$LETSENCRYPT_NO_EMAIL" == "1" ]]; then
    run_sudo certbot certonly \
      --manual \
      --preferred-challenges dns \
      --agree-tos \
      --register-unsafely-without-email \
      --cert-name "$BASE_DOMAIN" \
      -d "$BASE_DOMAIN" \
      -d "*.${BASE_DOMAIN}"
    return 0
  fi

  [[ -n "$LETSENCRYPT_EMAIL" ]] || die "set LETSENCRYPT_EMAIL (or LETSENCRYPT_NO_EMAIL=1)"

  run_sudo certbot certonly \
    --manual \
    --preferred-challenges dns \
    --agree-tos \
    --email "$LETSENCRYPT_EMAIL" \
    --cert-name "$BASE_DOMAIN" \
    -d "$BASE_DOMAIN" \
    -d "*.${BASE_DOMAIN}"
}

request_certificate() {
  case "$CERT_MODE" in
    apex)
      request_certificate_apex
      ;;
    wildcard)
      request_certificate_wildcard
      ;;
    *)
      die "invalid CERT_MODE=$CERT_MODE (expected: apex|wildcard)"
      ;;
  esac
}

show_renewal_status() {
  if [[ "$CERT_MODE" == "wildcard" ]]; then
    log "Skipping certbot renew --dry-run in wildcard/manual mode."
    log "Set up a DNS plugin or manual renewal runbook before expiry."
    return 0
  fi
  log "Checking renewal with dry-run"
  run_sudo certbot renew --dry-run || log "Dry-run renewal failed; check certbot/nginx logs"
}

main() {
  log "Preparing HTTPS for base domain: $BASE_DOMAIN (mode: $CERT_MODE)"
  ensure_certbot_installed
  ensure_nginx_ready
  request_certificate
  run_sudo nginx -t
  run_sudo systemctl reload nginx
  show_renewal_status
  log "Done. HTTPS should now be active for $BASE_DOMAIN"
}

main "$@"
