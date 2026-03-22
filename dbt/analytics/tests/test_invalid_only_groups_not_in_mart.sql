with invalid_groups as (

    select
        charged_partner as partner,
        month,
        currency
    from {{ ref('stg_premium_transactions') }}
    where is_valid_status = false
    group by 1, 2, 3

),

valid_processed_groups as (

    select
        charged_partner as partner,
        month,
        currency
    from {{ ref('stg_premium_transactions') }}
    where is_valid_status = true
      and status = 'processed'
    group by 1, 2, 3

),

invalid_only_groups as (

    select
        invalid_groups.partner,
        invalid_groups.month,
        invalid_groups.currency
    from invalid_groups
    left join valid_processed_groups
      on invalid_groups.partner = valid_processed_groups.partner
     and invalid_groups.month = valid_processed_groups.month
     and invalid_groups.currency = valid_processed_groups.currency
    where valid_processed_groups.partner is null

),

mart_groups as (

    select
        partner,
        month,
        currency
    from {{ ref('monthly_partner_premiums') }}

)

select
    mart_groups.*
from mart_groups
inner join invalid_only_groups
  on mart_groups.partner = invalid_only_groups.partner
 and mart_groups.month = invalid_only_groups.month
 and mart_groups.currency = invalid_only_groups.currency
