with expected as (

    select
        charged_partner as partner,
        month,
        currency,
        sum(amount)::numeric(18, 2) as total_premium
    from {{ ref('stg_premium_transactions') }}
    where is_valid_status = true
      and status = 'processed'
    group by 1, 2, 3

),

actual as (

    select
        partner,
        month,
        currency,
        total_premium
    from {{ ref('monthly_partner_premiums') }}

),

diff as (

    select * from expected
    except
    select * from actual

    union all

    select * from actual
    except
    select * from expected

)

select *
from diff
