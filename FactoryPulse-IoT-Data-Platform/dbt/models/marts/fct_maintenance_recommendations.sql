{{ config(materialized='view') }}

select
    device_id,
    device_type,
    location,
    zone,
    status,
    maintenance_due as overdue,
    cast(null as Nullable(Float64)) as health_score,
    today() as last_reading_date,
    days_since_maintenance,
    maintenance_interval_days,
    'Maintenance overdue. Schedule maintenance within the next 48 hours.' as recommendation,
    'high' as priority
from {{ ref('dim_devices') }}
where maintenance_due = 1
