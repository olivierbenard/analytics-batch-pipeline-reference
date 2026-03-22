#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

docker compose exec airflow bash -lc "
  set -euo pipefail

  airflow users delete \
    --username '${AIRFLOW_USER}' \
    || true

  airflow users create \
    --username '${AIRFLOW_USER}' \
    --firstname '${AIRFLOW_FIRSTNAME}' \
    --lastname '${AIRFLOW_LASTNAME}' \
    --role Admin \
    --email '${AIRFLOW_EMAIL}' \
    --password '${AIRFLOW_PASSWORD}'
"
