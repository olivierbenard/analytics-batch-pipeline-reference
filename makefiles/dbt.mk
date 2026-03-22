.PHONY: dbt-deps
dbt-deps:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt deps --profiles-dir /usr/app"

.PHONY: dbt-run
dbt-run:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt run --profiles-dir /usr/app"

.PHONY: dbt-test
dbt-test:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt test --profiles-dir /usr/app"

.PHONY: dbt-build
dbt-build:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt build --profiles-dir /usr/app"

.PHONY: dbt-docs-generate
dbt-docs-generate:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt docs generate --profiles-dir /usr/app"

.PHONY: dbt-docs-serve
dbt-docs-serve:
	docker compose exec dbt bash -lc "cd /usr/app/analytics && dbt docs serve --profiles-dir /usr/app --port 8081"

.PHONY: dbt-docs
dbt-docs: dbt-docs-generate dbt-docs-serve

.PHONY: dbt-refresh
dbt-refresh: dbt-build dbt-docs-generate
