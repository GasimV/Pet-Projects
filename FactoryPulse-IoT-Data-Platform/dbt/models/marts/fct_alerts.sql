{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by='(device_id, alert_timestamp)'
) }}

select
    a.alert_id,
    a.device_id,
    a.alert_type,
    a.severity,
    a.message,
    a.metric_name,
    a.metric_value,
    a.threshold,
    a.alert_timestamp,
    a.resolved,
    a.ingested_at,
    d.device_type,
    d.manufacturer,
    d.model,
    d.location,
    d.zone,
    d.status          as device_status,
    d.maintenance_due
from {{ ref('stg_alerts') }} as a
left join {{ ref('dim_devices') }} as d
    on a.device_id = d.device_id
