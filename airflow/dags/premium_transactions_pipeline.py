"""
Airflow DAG orchestrating the premium transactions pipeline.

Steps
-----
1. Load raw JSON transaction records into Postgres raw schema
2. Run dbt models for staging and marts
3. Export aggregated monthly premiums to CSV

The raw ingestion step intentionally preserves the source JSON payload
without parsing it. Downstream normalization and aggregation are handled
in dbt.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json

from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook
from airflow.models import Variable

ENCODING: str = "utf-8"
CSV_HEADER: list[str] = ["partner", "month", "currency", "total_premium"]


@dataclass(frozen=True)
class PipelineConfig:
    """
    Runtime configuration for the premium transactions pipeline.

    Attributes
    ----------
    conn_id : str
        Airflow connection identifier used to connect to Postgres.
    input_path : str
        Absolute path of the source JSON file mounted into the Airflow container.
    source_file : str
        Logical source file name stored in the raw table for lineage purposes.
    output_path : str
        Absolute path of the CSV output file to generate.
    dbt_project_dir : str
        Mounted dbt project directory inside the Airflow container.
    dbt_profiles_dir : str
        Mounted dbt profiles directory inside the Airflow container.
    ingestion_run_id : str
        Identifier written with each raw record for traceability.
    """

    conn_id: str
    input_path: str
    source_file: str
    output_path: str
    dbt_project_dir: str
    dbt_profiles_dir: str
    ingestion_run_id: str


@dataclass(frozen=True)
class RawEnvelope:
    """
    Raw transaction envelope ready to be inserted into Postgres.

    Attributes
    ----------
    ingestion_run_id : str
        Identifier of the current ingestion run.
    payload_json : dict[str, Any]
        Original source record preserved unchanged as JSON.
    payload_hash : str
        Deterministic SHA-256 hash of the canonicalized payload.
    source_file : str
        Source file name used for lineage.
    """

    ingestion_run_id: str
    payload_json: dict[str, Any]
    payload_hash: str
    source_file: str


def build_pipeline_config() -> PipelineConfig:
    """
    Build pipeline configuration from Airflow Variables.

    Returns
    -------
    PipelineConfig
        Fully resolved runtime configuration.
    """
    conn_id = Variable.get("premium_pipeline_conn_id")
    input_path = Variable.get("premium_pipeline_input_path")
    source_file = Variable.get("premium_pipeline_source_file")
    output_path = Variable.get("premium_pipeline_output_path")
    dbt_project_dir = Variable.get("dbt_project_dir")
    dbt_profiles_dir = Variable.get("dbt_profiles_dir")
    ingestion_run_id = f"airflow_manual__{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"

    return PipelineConfig(
        conn_id=conn_id,
        input_path=input_path,
        source_file=source_file,
        output_path=output_path,
        dbt_project_dir=dbt_project_dir,
        dbt_profiles_dir=dbt_profiles_dir,
        ingestion_run_id=ingestion_run_id,
    )


def validate_top_level_payload(payload: Any) -> None:
    """
    Validate the top-level JSON structure.

    Parameters
    ----------
    payload : Any
        Parsed JSON payload.

    Raises
    ------
    ValueError
        If the payload is not a list of JSON objects.
    """
    if not isinstance(payload, list):
        raise ValueError("Expected input JSON to be a list of transaction records.")

    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise ValueError(f"Expected record at index {index} to be a JSON object.")


def read_json_payload(input_path: str) -> list[dict[str, Any]]:
    """
    Read the source JSON file and return the raw payload.

    Parameters
    ----------
    input_path : str
        Absolute path to the source JSON file.

    Returns
    -------
    list[dict[str, Any]]
        Raw transaction records as dictionaries.

    Raises
    ------
    ValueError
        If the payload is not a list of JSON objects.
    """
    path = Path(input_path)

    with path.open("r", encoding=ENCODING) as file:
        payload = json.load(file)

    validate_top_level_payload(payload)

    return payload


def compute_payload_hash(record: dict[str, Any]) -> str:
    """
    Compute a deterministic SHA-256 hash for a raw JSON record.

    Parameters
    ----------
    record : dict[str, Any]
        Raw source record.

    Returns
    -------
    str
        Hex-encoded SHA-256 hash of the canonicalized payload.
    """
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode(ENCODING)).hexdigest()


def build_raw_envelopes(
    records: list[dict[str, Any]],
    config: PipelineConfig,
) -> list[RawEnvelope]:
    """
    Convert raw JSON records into insertion-ready raw envelopes.

    Parameters
    ----------
    records : list[dict[str, Any]]
        Raw source records.
    config : PipelineConfig
        Runtime pipeline configuration.

    Returns
    -------
    list[RawEnvelope]
        Raw envelopes ready for insertion.
    """
    return [
        RawEnvelope(
            ingestion_run_id=config.ingestion_run_id,
            payload_json=record,
            payload_hash=compute_payload_hash(record),
            source_file=config.source_file,
        )
        for record in records
    ]


def get_postgres_connection(conn_id: str):
    """
    Create a psycopg2 connection from an Airflow Connection.

    Parameters
    ----------
    conn_id : str
        Airflow connection identifier.

    Returns
    -------
    connection
        psycopg2 database connection.
    """
    conn = BaseHook.get_connection(conn_id)

    return psycopg2.connect(
        host=conn.host,
        port=conn.port,
        dbname=conn.schema,
        user=conn.login,
        password=conn.password,
    )


def insert_raw_envelopes(envelopes: list[RawEnvelope], conn_id: str) -> int:
    """
    Insert raw envelopes into raw.premium_transactions_raw.

    Duplicate payloads are ignored using the UNIQUE constraint on payload_hash.

    Parameters
    ----------
    envelopes : list[RawEnvelope]
        Raw envelopes to insert.
    conn_id : str
        Airflow connection identifier for Postgres.

    Returns
    -------
    int
        Number of source records attempted for insertion.
    """
    if not envelopes:
        return 0

    with get_postgres_connection(conn_id) as connection:
        with connection.cursor() as cursor:
            for envelope in envelopes:
                cursor.execute(
                    """
                    insert into raw.premium_transactions_raw (
                        ingestion_run_id,
                        payload_json,
                        payload_hash,
                        source_file
                    )
                    values (%s, %s, %s, %s)
                    on conflict (payload_hash) do nothing
                    """,
                    (
                        envelope.ingestion_run_id,
                        Json(envelope.payload_json),
                        envelope.payload_hash,
                        envelope.source_file,
                    ),
                )

        connection.commit()

    return len(envelopes)


def run_dbt_command(command: list[str], cwd: str) -> None:
    """
    Run a dbt command and fail loudly if it returns a non-zero exit code.

    Parameters
    ----------
    command : list[str]
        Full dbt command to execute.
    cwd : str
        Working directory where the dbt project lives.
    """
    subprocess.run(command, cwd=cwd, check=True)


def export_monthly_premiums_to_csv(
    conn_id: str, output_path: str, csv_header: None | list[str] = None
) -> Path:
    """
    Export marts.monthly_partner_premiums to a CSV file.

    Parameters
    ----------
    conn_id : str
        Airflow connection identifier for Postgres.
    output_path : str
        Output CSV path.

    Returns
    -------
    Path
        Written output file path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with get_postgres_connection(conn_id) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    partner,
                    month,
                    currency,
                    total_premium
                from marts.monthly_partner_premiums
                order by partner, month, currency
                """
            )
            rows = cursor.fetchall()

    if not csv_header:
        csv_header = CSV_HEADER

    with path.open("w", encoding=ENCODING, newline="") as file:
        writer = csv.writer(file)
        writer.writerow(csv_header)

        for partner, month, currency, total_premium in rows:
            writer.writerow(
                [
                    partner,
                    str(month),
                    currency,
                    f"{total_premium:.2f}",
                ]
            )

    return path


@task
def load_raw_transactions() -> int:
    """
    Load raw JSON transactions into the Postgres raw schema.

    Returns
    -------
    int
        Number of source records attempted for insertion.
    """
    config = build_pipeline_config()
    records = read_json_payload(config.input_path)
    envelopes = build_raw_envelopes(records, config)
    return insert_raw_envelopes(envelopes, config.conn_id)


@task
def build_dbt_models() -> None:
    """
    Run dbt deps and dbt build for the mounted dbt project.
    """
    config = build_pipeline_config()

    run_dbt_command(
        ["dbt", "deps", "--profiles-dir", config.dbt_profiles_dir],
        cwd=config.dbt_project_dir,
    )
    run_dbt_command(
        ["dbt", "build", "--profiles-dir", config.dbt_profiles_dir],
        cwd=config.dbt_project_dir,
    )


@task
def export_monthly_premiums() -> str:
    """
    Export the mart model to a CSV file.

    Returns
    -------
    str
        Output CSV path.
    """
    config = build_pipeline_config()
    output_file = export_monthly_premiums_to_csv(
        conn_id=config.conn_id,
        output_path=config.output_path,
    )
    return str(output_file)


@dag(
    dag_id="premium_transactions_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["premium", "pipeline", "raw"],
    description="Load raw premium transactions, run dbt staging/marts, and export CSV.",
)
def premium_transactions_pipeline_dag():
    """
    Define the premium transactions pipeline DAG.

    Current behaviour:
    - raw ingestion >> dbt build >> CSV export
    """
    load_raw_transactions_task = load_raw_transactions()
    build_dbt_models_task = build_dbt_models()
    export_monthly_premiums_task = export_monthly_premiums()

    load_raw_transactions_task >> build_dbt_models_task >> export_monthly_premiums_task


premium_transactions_pipeline = premium_transactions_pipeline_dag()
