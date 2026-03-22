with raw as (

    select
        ingestion_run_id,
        ingested_at,
        payload_hash,
        source_file,
        payload_json
    from {{ source('raw', 'premium_transactions_raw') }}

),

parsed as (

    select
        ingestion_run_id,
        ingested_at,
        payload_hash,
        source_file,

        trim(payload_json ->> 'transaction_id') as transaction_id,

        to_timestamp(
            trim(payload_json ->> 'created_at'),
            'MM/DD/YYYY HH24:MI:SS'
        ) as created_at,

        date_trunc(
            'month',
            to_timestamp(
                trim(payload_json ->> 'created_at'),
                'MM/DD/YYYY HH24:MI:SS'
            )
        )::date as month,

        (payload_json ->> 'amount')::numeric(18, 2) as amount,
        upper(trim(payload_json ->> 'currency')) as currency,
        trim(payload_json ->> 'charged_partner') as charged_partner,
        lower(trim(payload_json ->> 'status')) as status

    from raw

),

validated as (

    select
        ingestion_run_id,
        ingested_at,
        payload_hash,
        source_file,
        transaction_id,
        created_at,
        month,
        amount,
        currency,
        charged_partner,
        status,

        case
            when status in ('processed', 'failed', 'refunded')
            then true
            else false
        end as is_valid_status

    from parsed

)

select *
from validated
