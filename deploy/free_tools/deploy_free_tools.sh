#!/usr/bin/env bash
# deploy_free_tools.sh — Infisical + Healthchecks.io self-hosted (M5, SO_TOTAL_CI)
# Dreams2Memories Travel · Thunderbird Wing · 2026-07-01
#
# WHY THIS SCRIPT (not `docker compose`): this host has NO compose plugin.
# Pure `docker run` so it works anywhere docker is reachable.
#
# RUN IT (in a shell where the docker group is active — Commander's interactive
# shell, or a freshly-restarted Claude session):
#     bash deploy/free_tools/deploy_free_tools.sh
# Secrets are generated once and saved to deploy/free_tools/.secrets (chmod 600).
set -euo pipefail

ROOT="/home/john/Thunderbird"
SECRETS="$ROOT/deploy/free_tools/.secrets"
HC_PORT=8123          # Healthchecks  (dead-man switches)
INF_PORT=8899         # Infisical     (secrets manager)

gen() { openssl rand -hex 16; }
gen32() { openssl rand -base64 32; }

mkdir -p "$(dirname "$SECRETS")"
if [[ ! -f "$SECRETS" ]]; then
  cat > "$SECRETS" <<EOF
HC_SECRET_KEY=$(gen32)
HC_SUPERUSER_PW=$(gen)
INF_ENCRYPTION_KEY=$(gen)
INF_AUTH_SECRET=$(gen32)
INF_PG_PW=$(gen)
EOF
  chmod 600 "$SECRETS"
  echo "[secrets] generated → $SECRETS (chmod 600)"
fi
# shellcheck disable=SC1090
source "$SECRETS"

echo "== docker preflight =="
docker version --format 'server {{.Server.Version}}' || { echo "docker not reachable — run in a docker-group shell"; exit 1; }

# ---------------------------------------------------------------- Healthchecks
echo "== Healthchecks.io (dead-man switches) :$HC_PORT =="
docker rm -f healthchecks 2>/dev/null || true
docker run -d --name healthchecks --restart unless-stopped \
  -p "$HC_PORT:8000" \
  -e SECRET_KEY="$HC_SECRET_KEY" \
  -e DEBUG=False \
  -e DB=sqlite \
  -e SITE_ROOT="http://localhost:$HC_PORT" \
  -e SITE_NAME="Thunderbird Deadman" \
  -e ALLOWED_HOSTS='*' \
  -e SUPERUSER_EMAIL="johnloucks3@gmail.com" \
  -e SUPERUSER_PASSWORD="$HC_SUPERUSER_PW" \
  -e REGISTRATION_OPEN=False \
  -v healthchecks-data:/data \
  healthchecks/healthchecks:latest
echo "[ok] Healthchecks → http://localhost:$HC_PORT  (login johnloucks3@gmail.com / see .secrets HC_SUPERUSER_PW)"

# ------------------------------------------------------------------- Infisical
echo "== Infisical (secrets manager) :$INF_PORT =="
docker network create infisical-net 2>/dev/null || true

docker rm -f infisical-postgres 2>/dev/null || true
docker run -d --name infisical-postgres --network infisical-net --restart unless-stopped \
  -e POSTGRES_USER=infisical -e POSTGRES_PASSWORD="$INF_PG_PW" -e POSTGRES_DB=infisical \
  -v infisical-pg:/var/lib/postgresql/data postgres:14-alpine

docker rm -f infisical-redis 2>/dev/null || true
docker run -d --name infisical-redis --network infisical-net --restart unless-stopped \
  -v infisical-redis:/data redis:7-alpine

echo "[wait] letting postgres come up (10s)…"; sleep 10

docker rm -f infisical 2>/dev/null || true
docker run -d --name infisical --network infisical-net --restart unless-stopped \
  -p "$INF_PORT:8080" \
  -e ENCRYPTION_KEY="$INF_ENCRYPTION_KEY" \
  -e AUTH_SECRET="$INF_AUTH_SECRET" \
  -e DB_CONNECTION_URI="postgres://infisical:$INF_PG_PW@infisical-postgres:5432/infisical" \
  -e REDIS_URL="redis://infisical-redis:6379" \
  -e SITE_URL="http://localhost:$INF_PORT" \
  infisical/infisical:latest-postgres
echo "[ok] Infisical → http://localhost:$INF_PORT  (first visit = create admin account)"

echo ""
echo "== DONE. Verify: =="
echo "  docker ps | grep -E 'healthchecks|infisical'"
echo "  curl -sf http://localhost:$HC_PORT/  >/dev/null && echo HC-UP"
echo "  curl -sf http://localhost:$INF_PORT/ >/dev/null && echo INF-UP"
echo ""
echo "Then tell Hale 'tools up' — she runs the CI probes + registers both as CI skills."
echo "NOTE: client-path secrets migrate into Infisical only on a 7-day internal canary (Sterling guardrail)."
