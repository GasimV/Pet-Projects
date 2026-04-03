{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by='device_id'
) }}

select
    device_id,
    device_type,
    manufacturer,
    model,
    install_date,
    location,
    zone,
    maintenance_interval_days,
    last_maintenance_date,
    days_since_maintenance,
    status,
    if(days_since_maintenance > maintenance_interval_days, 1, 0) as maintenance_due,
    updated_at
from {{ ref('stg_devices') }}
