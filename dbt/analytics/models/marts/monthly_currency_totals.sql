with source as (

    select
        month,
        currency,
        total_premium
    from {{ ref('monthly_partner_premiums') }}

),

aggregated as (

    select
        month,
        currency,
        sum(total_premium)::numeric(18, 2) as total_premium
    from source
    group by 1, 2

)

select
    month,
    currency,
    total_premium
from aggregated
order by month, currency
