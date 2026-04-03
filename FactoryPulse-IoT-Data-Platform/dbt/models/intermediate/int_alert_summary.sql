{{ config(materialized='view') }}

select
    device_id,
    alert_type,
    severity,
    toDate(alert_timestamp) as alert_date,
    count()                 as alert_count
from {{ ref('stg_alerts') }}
group by
    device_id,
    alert_type,
    severity,
    toDate(alert_timestamp)
