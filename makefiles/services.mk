include .env
export

POSTGRES_SERVICE := analytics-batch-pipeline-reference-postgres-1
DBT_SERVICE := analytics-batch-pipeline-reference-dbt-1
AIRFLOW_SERVICE := analytics-batch-pipeline-reference-airflow-1

.PHONY: fernet_key
fernet_key:
	@poetry run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

.PHONY: up
up:
	docker compose --env-file .env up --build -d

.PHONY: airflow-init
airflow-init:
	./airflow/init_airflow.sh

.PHONY: wait-airflow
wait-airflow:
	@echo "Waiting for Airflow..."
	@until curl -s http://localhost:8080/health | grep -q healthy; do \
		sleep 2; \
	done

.PHONY: init
init: up wait-airflow airflow-init

.PHONY: down
down:
	docker compose down

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: ps
ps:
	docker compose ps

.PHONY: check-postgres
check-postgres:
	docker exec $(POSTGRES_SERVICE) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT * FROM raw.premium_transactions_raw WHERE 1 = 0;"

.PHONY: check-schemas
check-schemas:
	docker exec $(POSTGRES_SERVICE) psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;"

.PHONY: check-airflow
check-airflow:
	docker exec $(AIRFLOW_SERVICE) airflow version
	@echo "Checking Airflow variables..."
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_PREMIUM_PIPELINE_CONN_ID="
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_PREMIUM_PIPELINE_INPUT_PATH="
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_PREMIUM_PIPELINE_SOURCE_FILE="
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_PREMIUM_PIPELINE_OUTPUT_PATH="
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_DBT_PROJECT_DIR="
	@docker compose exec airflow bash -lc "env | grep AIRFLOW_VAR_DBT_PROFILES_DIR="
	@echo "Airflow variables OK"

.PHONY: check-dbt
check-dbt:
	docker exec $(DBT_SERVICE) dbt --version

.PHONY: check-init
check-init: check-postgres check-airflow check-dbt

.PHONY: clean
clean:
	docker compose down -v --remove-orphans
