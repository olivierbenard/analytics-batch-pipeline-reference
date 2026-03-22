# Python part
PACKAGE_NAME := batch_pipeline_reference

.PHONY: run
run:
	poetry run python $(PACKAGE_NAME)/main.py --input ./input/premium_transactions_data_20250306.json --output ./output/output.csv

.PHONY: ruff
ruff:
	poetry run ruff check --select I --fix & \
	poetry run ruff format .

.PHONY: ruff-check
ruff-check:
	poetry run ruff check .


.PHONY: mypy
mypy:
	poetry run mypy $(PACKAGE_NAME)

.PHONY: pylint
pylint:
	poetry run pylint $(PACKAGE_NAME)

.PHONY: test
test:
	poetry run pytest -vvs tests/

.PHONY: coverage
coverage:
		poetry run pytest --cov=$(PACKAGE_NAME) --cov-report=term-missing --cov-fail-under=80

.PHONY: checks
checks: ruff-check mypy pylint test coverage

.PHONY: clean-python
clean-python:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name ".coverage" -exec rm -rf {} +
