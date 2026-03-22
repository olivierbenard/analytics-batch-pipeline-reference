# Business Analysis of Aggregated Premium Transactions

## Overview

The pipeline aggregates processed premium transactions per `partner`, `month`, and `currency`.
The resulting dataset provides a compact operational view of how insurance premiums evolve over time across distribution partners.

The data spans **June to September 2024** and includes four partners:

- berlinre
- dronant
- getland
- liadigital

Two currencies appear in the dataset:

- EUR (dominant)
- GBP (minor share)

# Key Business Observations

## EUR premiums dominate revenue

Across all partners and months, **EUR represents the overwhelming majority of premium volume**.

GBP transactions exist but represent only a **small fraction of total premiums**.
This suggests either:

- most customers transact in EUR
- GBP transactions correspond to a smaller geographic segment

From a business perspective this means:

- EUR is the primary reporting currency
- GBP volumes should likely be converted or reported separately in financial dashboards.

## Premium activity peaks in June

June shows the highest premium volume across all partners.

Possible explanations:

- seasonal campaign activity
- policy renewals clustered in early summer
- onboarding spikes from marketing campaigns

From July onward, premiums gradually decrease.
This may reflect a **natural "cohort decay" after policy creation**.

## Partner contribution differences

Partners contribute differently to premium generation:

Approximate EUR totals:

| Partner    | Relative contribution |
|------------|-----------------------|
| dronant    | highest (33%)         |
| liadigital | high (25%)            |
| getland    | medium (22%)          |
| berlinre   | lower (19%)           |

This suggests _dronant_ and _liadigital_ are the strongest distribution channels in this dataset.

For business stakeholders this information could support:

- partner performance monitoring
- commission modelling
- distribution strategy adjustments

## September contains partial activity

September contains significantly fewer transactions compared to other months.

This likely means the dataset contains **partial data for that month** rather than a true drop in business performance.

Operational reporting pipelines should normally flag partial months explicitly.

# Data Engineering Trade-offs

During implementation several design decisions had to be taken.

## Handling multiple currencies

The initial specification suggested aggregating: `partner` and `month` to obtain the total_premium.

However the source data contains **multiple currencies (EUR and GBP)**.

Aggregating them together would produce financially incorrect results.

Two possible approaches were considered:

| Option                                            | Outcome                                               |
|---------------------------------------------------|-------------------------------------------------------|
| Fail the pipeline when multiple currencies appear | prevents incorrect aggregation but produces no output |
| Convert currencies                                | requires FX rates and assumptions                     |
| **Aggregate per currency**                        | preserves correctness without assumptions             |

The final implementation extends the schema to: `partner`, `month`, `currency` aggregation to obtain the total_premium

This ensures monetary values are **never mixed**.

## Raw ingestion strategy

Instead of directly parsing the JSON structure into relational columns, the ingestion layer stores the original payload in a **raw JSON envelope**.

Advantages:

- schema changes upstream do not break ingestion
- _replayability_ of historical payloads
- easier debugging of malformed records

Parsing and normalization are handled in downstream transformation steps.

## 3. Strict validation layer

Transactions are validated before transformation:

- currency normalized to ISO format
- timestamps validated
- numeric values converted to Decimal
- invalid records collected with error messages

This prevents corrupted data from contaminating the aggregation layer.

## Dual implementation strategy

Two implementations were considered:

1. **Python batch pipeline**
2. **Data stack version (Airflow + dbt + Postgres)**

The Python implementation was developed first to:

- validate business logic
- produce a reference output
- simplify testing

This reference implementation can then be mirrored in the orchestrated stack.

# Duplicate Handling Note

## Why this change was needed

While comparing the results produced by the **Airflow + Postgres + dbt** execution path and the **standalone Python batch job**, I found a discrepancy in the final aggregated output.

The exact mismatches:

```text
dronant,2024-07-01,EUR,1754.42     (Python)
dronant,2024-07-01,EUR,1749.48     (Airflow)
liadigital,2024-06-01,EUR,2197.32  (Python)
liadigital,2024-06-01,EUR,2193.12  (Airflow)
```

At first glance, this looked like a transformation mismatch. In reality, the difference came from **deduplication behaviour at ingestion time**.

## Root cause

The Airflow / Postgres path inserts raw records with:

```sql
insert into raw.premium_transactions_raw (...)
values (...)
on conflict (payload_hash) do nothing
```

This is a **strong native SQL pattern** because **PostgreSQL can enforce idempotent ingestion directly at the storage layer** through a unique constraint on `payload_hash`.

The original Python batch path did **not** apply the same deduplication rule before validation and transformation. As a result, duplicate raw payloads were still being aggregated in the Python output, while the Airflow path silently ignored them during ingestion.

## Why this is interesting

This is a good example of how **the right tool can save the day**:

- SQL provides a native and elegant way to enforce idempotency.
- The warehouse path exposed a hidden assumption in the Python reference implementation.
- Comparing both execution paths surfaced a semantic mismatch that would have been easy to miss otherwise.

In other words, the platform-oriented implementation did not just reproduce the Python logic - it helped improve it.

## Refactoring applied to the Python path

To align both execution paths, I introduced two helper methods in the Python batch job:

- `compute_payload_hash(record)`: Computes a deterministic SHA-256 hash from the canonical JSON representation of a raw record.
- `deduplicate_raw_records(records)`: Removes duplicate raw records while preserving first-seen order.

This change makes the Python reference implementation consistent with the ingestion semantics already enforced in PostgreSQL.

## Practical lesson

The most important lesson here is that **consistency between execution paths matters more than implementation language**.

If the Airflow / warehouse path defines the intended ingestion semantics as:

- keep raw payloads unchanged
- deduplicate identical payloads by hash
- aggregate only unique records

then the Python reference path should apply the same rule before transformation.

That alignment removed the discrepancy and triggered a useful round of refactoring in the Python code.

# Conclusion

The aggregated results provide a clear monthly view of premium generation across partners.
The data highlights partner performance differences and confirms that EUR dominates premium volume.

From an engineering perspective, the pipeline prioritizes:

- data correctness
- explicit handling of currency differences
- reproducibility of ingestion
- transparent validation of input records

These design decisions aim to balance **robust data engineering practices with business‑relevant outputs**.
