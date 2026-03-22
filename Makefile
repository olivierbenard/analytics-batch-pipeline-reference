include makefiles/python.mk
include makefiles/services.mk
include makefiles/pre_commit.mk
include makefiles/dbt.mk

# starts a one-off container, run it with CLI-args and delete it
.PHONY: run-python-batch
run-python-batch:
	docker compose --profile batch run --rm python-batch \
	--input ./input/premium_transactions_data_20250306.json \
	--output ./output/output.csv
