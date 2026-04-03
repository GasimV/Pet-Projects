-- Custom test: ensure all health scores fall within the valid 0-100 range.
-- dbt expects this query to return zero rows if the test passes.

select
    device_id,
    reading_date,
    health_score
from {{ ref('fct_device_health') }}
where health_score < 0 or health_score > 100
