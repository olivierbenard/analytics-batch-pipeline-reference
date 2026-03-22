select *
from {{ ref('monthly_partner_premiums') }}
where total_premium <= 0
