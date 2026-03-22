with filtered as (

    select
        charged_partner as partner,
        month,
        currency,
        amount
    from {{ ref('stg_premium_transactions') }}
    where is_valid_status = true
      and status = 'processed'

),

aggregated as (

    select
        partner,
        month,
        currency,
        sum(amount)::numeric(18, 2) as total_premium
    from filtered
    group by 1, 2, 3

)

select
    partner,
    month,
    currency,
    total_premium
from aggregated
order by partner, month, currency
